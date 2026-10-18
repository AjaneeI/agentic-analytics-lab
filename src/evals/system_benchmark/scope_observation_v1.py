"""Conservative executed-SQL population observation, version 1.

This proves only the row population for a small supported SQL grammar. It is
not a SQL safety guard, metric-expression validator, or general SQL parser.
Unknown SQL must remain unknown; call only after a successful nonempty query.
"""
from __future__ import annotations
import re

OBSERVATION_VERSION = 'runtime-sql-scope-v1'
_TOKEN = re.compile(r"\s+|'(?:''|[^'\\])*'|`[A-Za-z_][A-Za-z_0-9]*`|\"[A-Za-z_][A-Za-z_0-9]*\"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+(?:\.[0-9]+)?|!=|<>|[().,=+*/%<>-]")
_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')
_FORBIDDEN = frozenset('with join union intersect except prewhere having window qualify sample final settings offset array limitby'.split())


def _tokens(sql: str) -> list[str] | None:
    """Normalize identifiers but preserve SQL string literal case exactly."""
    if "--" in sql or "/*" in sql or ";" in sql:
        return None
    output = []
    position = 0
    for match in _TOKEN.finditer(sql):
        if match.start() != position:
            return None
        token = match.group()
        position = match.end()
        if token.isspace():
            continue
        if token.startswith("'"):
            output.append(token)
        else:
            output.append(token.strip('`"').lower())
    if position != len(sql):
        return None
    return output


def _unwrap(tokens: list[str]) -> list[str]:
    while len(tokens) > 1 and tokens[0] == '(' and tokens[-1] == ')':
        depth = 0
        wraps = True
        for token in tokens[:-1]:
            depth += (token == '(') - (token == ')')
            if depth == 0:
                wraps = False
                break
        if not wraps:
            break
        tokens = tokens[1:-1]
    return tokens


def _supported_tail(tokens: list[str], alias: str | None) -> bool:
    """Consume the entire optional GROUP/ORDER/LIMIT suffix, in that order."""
    index = 0
    team_refs = [['team'], ['delivery_work_items', '.', 'team']]
    if alias:
        team_refs.append([alias, '.', 'team'])
    if tokens[:2] == ['group', 'by']:
        index = 2
        ref = next((ref for ref in team_refs if tokens[index:index + len(ref)] == ref), None)
        if ref is None:
            return False
        index += len(ref)
    if tokens[index:index + 2] == ['order', 'by']:
        index += 2
        order_refs = [['blocked_pct'], ['blocker_rate']] + team_refs
        while True:
            ref = next((ref for ref in order_refs if tokens[index:index + len(ref)] == ref), None)
            if ref is None:
                return False
            index += len(ref)
            if tokens[index:index + 1] in (['asc'], ['desc']):
                index += 1
            if tokens[index:index + 1] != [',']:
                break
            index += 1
    if tokens[index:index + 1] == ['limit']:
        index += 1
        if index >= len(tokens) or not tokens[index].isdigit():
            return False
        index += 1
    return index == len(tokens)


def derive_population_scope(sql: str) -> str | None:
    """Recognize only direct-table, active-only SELECTs; never infer from labels."""
    tokens = _tokens(sql)
    if not tokens or tokens[0] != 'select' or tokens.count('select') != 1:
        return None
    if any(token in _FORBIDDEN for token in tokens):
        return None
    depth = 0
    top: list[tuple[int, str]] = []
    for index, token in enumerate(tokens):
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
            if depth < 0:
                return None
        elif depth == 0:
            top.append((index, token))
    if depth:
        return None
    froms = [index for index, token in top if token == 'from']
    wheres = [index for index, token in top if token == 'where']
    if len(froms) != 1 or len(wheres) != 1:
        return None
    from_index, where_index = froms[0], wheres[0]
    if from_index >= where_index or any(
        token.strip("'").casefold() == 'status' for token in tokens[1:from_index]
    ):
        # ClickHouse SELECT aliases can shadow WHERE columns. Reject even a
        # direct status projection rather than trying to resolve alias binding.
        return None
    table = tokens[from_index + 1:where_index]
    prefix = ['agentic_analytics', '.', 'delivery_work_items']
    if table[:3] != prefix:
        return None
    alias_tokens = table[3:]
    if alias_tokens[:1] == ['as']:
        alias_tokens = alias_tokens[1:]
    if len(alias_tokens) > 1 or (alias_tokens and not _IDENTIFIER.fullmatch(alias_tokens[0])):
        return None
    alias = alias_tokens[0] if alias_tokens else None
    end = next((index for index, token in top if index > where_index and token in ('group', 'order', 'limit')), len(tokens))
    if not _supported_tail(tokens[end:], alias):
        return None
    predicate = _unwrap(tokens[where_index + 1:end])
    # Resolve only unambiguous references to the one direct source.
    refs = [['status'], ['delivery_work_items', '.', 'status'], prefix + ['.', 'status']]
    if alias:
        refs.append([alias, '.', 'status'])
    for ref in refs:
        for op in ('!=', '<>'):
            if predicate == ref + [op, "'done'"] or predicate == ["'done'", op] + ref:
                return 'active_work_items'
        if predicate == ref + ['not', 'in', '(', "'done'", ')']:
            return 'active_work_items'
        if predicate[:1] == ['not']:
            inner = _unwrap(predicate[1:])
            if inner == ref + ['=', "'done'"] or inner == ["'done'", '='] + ref:
                return 'active_work_items'
    return None
