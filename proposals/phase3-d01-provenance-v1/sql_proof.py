"""Inactive, bounded relational proof interpreter. Does NOT execute SQL.

Whole-input parsing, lexical alias scopes and exact aggregate polynomials.
This is not a general SQL parser, security guard or live capture adapter.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import re

class Unsupported(ValueError):
    pass

class Contradiction(ValueError):
    pass

# Polynomial monomials: powers of raw binary B, grouped numerator N, denominator D.
def poly(value=0, powers=(0, 0, 0)):
    return {powers: F(value)} if value else {}

B, N, D = poly(1, (1,0,0)), poly(1, (0,1,0)), poly(1, (0,0,1))

def add(a, b, sign=1):
    out = dict(a)
    for key, value in b.items():
        out[key] = out.get(key, F(0)) + sign * value
    return {key:value for key,value in out.items() if value}

def multiply(a, b):
    out = {}
    for ka, va in a.items():
        for kb, vb in b.items():
            key = tuple(x+y for x,y in zip(ka,kb))
            out[key] = out.get(key,F(0)) + va*vb
    return {key:value for key,value in out.items() if value}

def divide(a, b):
    if len(b) != 1:
        raise Unsupported("non_monomial_denominator")
    key,value = next(iter(b.items()))
    if key[0]!=0 or key[1]!=0:
        raise Contradiction("metric_lineage_not_proven")
    return multiply(a, {tuple(-x for x in key):1/value})

RATE = divide(multiply(poly(100),N),D)

@dataclass(frozen=True)
class Cell:
    value: object
    lineage: object

@dataclass
class Relation:
    rows: list
    lineage: dict
    scope: str = "all"
    grouped: bool = False
    full_domain: bool = True
    ordered: bool = False
    limited: bool = False

TOKEN = re.compile(r"\s+|'(?:''|[^'\\])*'|`[A-Za-z_][A-Za-z_0-9]*`|\"[A-Za-z_][A-Za-z_0-9]*\"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+(?:\.[0-9]+)?|!=|<>|<=|>=|[().,=+*/<>-]")
WORDS = set("select from as where group by order asc desc limit with and or not in then else end when".split())

def tokens(sql):
    if not isinstance(sql,str) or len(sql)>8192:
        raise Unsupported("query_size")
    out=[];pos=0
    for match in TOKEN.finditer(sql):
        if match.start()!=pos:
            raise Unsupported("unsupported_token")
        token=match.group();pos=match.end()
        if token.isspace():
            continue
        out.append(token if token.startswith("'") else token.strip('`"').lower())
    if pos!=len(sql) or len(out)>1024:
        raise Unsupported("unsupported_token_or_size")
    return out

class Parser:
    def __init__(self, sql):
        self.t=tokens(sql);self.i=0;self.depth=0

    def peek(self):
        return self.t[self.i] if self.i<len(self.t) else ""

    def take(self, value=None):
        token=self.peek()
        if not token or value is not None and token!=value:
            raise Unsupported("expected_"+str(value))
        self.i+=1;return token

    def accept(self, value):
        if self.peek()==value:
            self.i+=1;return True
        return False

    def ident(self):
        token=self.take()
        if not re.fullmatch(r"[a-z_][a-z_0-9]*",token) or token in WORDS:
            raise Unsupported("identifier")
        return token

    def expression(self, minimum=0):
        self.depth+=1
        if self.depth>32:
            raise Unsupported("expression_depth")
        token=self.take()
        if token=="(":
            node=self.expression();self.take(")")
        elif token=="not":
            node=("not",self.expression(3))
        elif token in ("+","-"):
            node=(token,("literal",F(0)),self.expression(6))
        elif token=="case":
            self.take("when");condition=self.expression();self.take("then")
            yes=self.expression();self.take("else");no=self.expression();self.take("end")
            node=("case",condition,yes,no)
        elif token.startswith("'"):
            node=("literal",token[1:-1].replace("''","'"))
        elif re.fullmatch(r"[0-9]+(?:\.[0-9]+)?",token):
            node=("literal",F(token))
        elif token=="null":
            node=("literal",None)
        elif re.fullmatch(r"[a-z_][a-z_0-9]*",token):
            if self.accept("("):
                if self.accept("*"):
                    args=[("star",)]
                else:
                    args=[self.expression()]
                self.take(")");node=("function",token,*args)
            else:
                names=[token]
                while self.accept("."):
                    names.append(self.ident())
                node=("column",tuple(names))
        else:
            raise Unsupported("expression")
        precedences={"or":1,"and":2,"=":3,"!=":3,"<>":3,"<":3,">":3,"<=":3,">=":3,"+":4,"-":4,"*":5,"/":5}
        while True:
            op=self.peek()
            if op=="not" and self.i+1<len(self.t) and self.t[self.i+1]=="in" and minimum<=3:
                self.take("not");self.take("in");self.take("(")
                item=self.expression();self.take(")");node=("notin",node,item);continue
            if op not in precedences or precedences[op]<minimum:
                break
            self.take();node=(op,node,self.expression(precedences[op]+1))
        self.depth-=1;return node

    def select(self):
        self.take("select");projection=[]
        while True:
            node=self.expression()
            if self.accept("as"):
                name=self.ident()
            elif node[0]=="column":
                name=node[1][-1]
            else:
                raise Unsupported("explicit_expression_alias_required")
            if any(name==old for old,_ in projection):
                raise Unsupported("duplicate_output_alias")
            projection.append((name,node))
            if not self.accept(","):
                break
        self.take("from");source=[self.ident()]
        while self.accept("."):
            source.append(self.ident())
        alias=None
        if self.accept("as"):
            alias=self.ident()
        elif self.peek() and re.fullmatch(r"[a-z_][a-z_0-9]*",self.peek()) and self.peek() not in WORDS:
            alias=self.ident()
        predicate=self.expression() if self.accept("where") else None
        group=None
        if self.accept("group"):
            self.take("by");group=self.expression()
        order=[]
        if self.accept("order"):
            self.take("by")
            while True:
                node=self.expression();direction=self.take() if self.peek() in ("asc","desc") else "asc"
                order.append((node,direction))
                if not self.accept(","):
                    break
        limit=None
        if self.accept("limit"):
            token=self.take()
            if not token.isdigit() or not 1<=int(token)<=10000:
                raise Unsupported("limit")
            limit=int(token)
        return dict(projection=projection,source=tuple(source),alias=alias,predicate=predicate,group=group,order=order,limit=limit)

    def parse(self):
        ctes=[]
        if self.accept("with"):
            while True:
                name=self.ident()
                if name=="delivery_work_items" or any(name==n for n,_ in ctes) or len(ctes)>=3:
                    raise Unsupported("cte_binding_or_limit")
                self.take("as");self.take("(");query=self.select();self.take(")")
                ctes.append((name,query))
                if not self.accept(","):
                    break
        final=self.select()
        if self.i!=len(self.t):
            raise Unsupported("unconsumed_sql")
        return ctes,final

def resolve(node, row, qualifiers):
    names=node[1]
    if len(names)>1 and names[:-1] not in qualifiers:
        raise Unsupported("unknown_qualifier")
    try:
        return row[names[-1]]
    except KeyError:
        raise Unsupported("unknown_column") from None

def active_predicate(node, row, qualifiers):
    def kind(x):
        return resolve(x,row,qualifiers).lineage if x[0]=="column" else x
    if node[0] in ("!=","<>","notin"):
        a,b=kind(node[1]),kind(node[2])
        return (a,b)==(("base","status"),("literal","done")) or node[0]!="notin" and (b,a)==(("base","status"),("literal","done"))
    if node[0]=="not" and node[1][0]=="=":
        a,b=kind(node[1][1]),kind(node[1][2])
        return (a,b)==(("base","status"),("literal","done")) or (b,a)==(("base","status"),("literal","done"))
    return False

def has_aggregate(node):
    return node[0]=="function" or any(has_aggregate(x) for x in node[1:] if isinstance(x,tuple) and x and isinstance(x[0],str))

def evaluate(node,row,qualifiers,group=None):
    op=node[0]
    if op=="literal":
        val=node[1];return Cell(val,poly(val) if isinstance(val,F) else node)
    if op=="column":
        cell=resolve(node,row,qualifiers)
        if group is not None and cell.lineage!=("base","team"):
            raise Unsupported("ungrouped_column")
        return cell
    if op=="function":
        if group is None or node[1] not in ("sum","count","avg"):
            raise Unsupported("aggregate_function_or_context")
        arg=node[2]
        if arg[0]=="star":
            if node[1]!="count":
                raise Unsupported("star")
            return Cell(F(len(group)),D)
        vals=[evaluate(arg,r,qualifiers) for r in group]
        lineage=evaluate(arg,row,qualifiers).lineage
        if node[1]=="count":
            if lineage!=B:
                raise Unsupported("count_expression")
            return Cell(F(len(vals)),D)
        if not isinstance(lineage,dict):
            raise Unsupported("aggregate_operand")
        if lineage==B:
            proof=N
        elif all(k==(0,0,0) for k in lineage):
            proof=multiply(lineage,D)
        else:
            raise Unsupported("aggregate_operand")
        value=sum((v.value for v in vals),F(0))
        if node[1]=="avg":
            return Cell(value/len(vals) if vals else None,divide(proof,D))
        return Cell(value,proof)
    if op=="case":
        condition=evaluate(node[1],row,qualifiers,group)
        yes=evaluate(node[2],row,qualifiers,group);no=evaluate(node[3],row,qualifiers,group)
        if node[1][0]=="=":
            lhs=evaluate(node[1][1],row,qualifiers);rhs=evaluate(node[1][2],row,qualifiers)
            binary=lhs.lineage==B and rhs.value==1 or rhs.lineage==B and lhs.value==1
            if binary and yes.lineage==poly(1) and no.lineage==poly(0):
                return Cell(yes.value if condition.value else no.value,B)
        if node[1][1][0]==node[1][2][0]=="literal":
            return yes if condition.value else no
        raise Unsupported("case_expression")
    if op=="not":
        return Cell(not evaluate(node[1],row,qualifiers).value,None)
    a=evaluate(node[1],row,qualifiers,group);b=evaluate(node[2],row,qualifiers,group)
    if op in ("+","-","*","/"):
        if not isinstance(a.lineage,dict) or not isinstance(b.lineage,dict):
            raise Unsupported("arithmetic_operand")
        proof={"+":lambda:add(a.lineage,b.lineage),"-":lambda:add(a.lineage,b.lineage,-1),"*":lambda:multiply(a.lineage,b.lineage),"/":lambda:divide(a.lineage,b.lineage)}[op]()
        if a.value is None or b.value is None or op=="/" and b.value==0:
            value=None
        else:
            value={"+":lambda:a.value+b.value,"-":lambda:a.value-b.value,"*":lambda:a.value*b.value,"/":lambda:a.value/b.value}[op]()
        return Cell(value,proof)
    operations={"=":lambda:a.value==b.value,"!=":lambda:a.value!=b.value,"<>":lambda:a.value!=b.value,"notin":lambda:a.value!=b.value,"and":lambda:bool(a.value and b.value),"or":lambda:bool(a.value or b.value),"<":lambda:a.value<b.value,">":lambda:a.value>b.value,"<=":lambda:a.value<=b.value,">=":lambda:a.value>=b.value}
    if op not in operations:
        raise Unsupported("operator")
    return Cell(operations[op](),None)

def interpret(query,environment,final=False):
    source=query["source"]
    if source in (("delivery_work_items",),("agentic_analytics","delivery_work_items")):
        relation=environment["delivery_work_items"]
    elif len(source)==1 and source[0] in environment:
        relation=environment[source[0]]
    else:
        raise Contradiction("wrong_source")
    qualifiers={source,source[-1:]}
    if query["alias"]:
        qualifiers={(query["alias"],)}
    prototype={name:Cell(None,lineage) for name,lineage in relation.lineage.items()}
    for alias,node in query["projection"]:
        if alias in relation.lineage and node!=("column",(alias,)):
            try:
                same=node[0]=="column" and resolve(node,prototype,qualifiers).lineage==relation.lineage[alias]
            except Unsupported:
                same=False
            if not same:
                raise Unsupported("alias_shadowing")
    rows=relation.rows;scope=relation.scope
    if query["predicate"] is not None:
        if relation.grouped:
            raise Unsupported("postaggregate_filter")
        if not active_predicate(query["predicate"],prototype,qualifiers):
            selected=[r for r in rows if evaluate(query["predicate"],r,qualifiers).value]
            active=[r for r in rows if r.get("status",Cell(None,None)).value!="done"]
            if selected!=active:
                raise Contradiction("wrong_population")
            raise Unsupported("population_equivalence_not_proven")
        scope="active"
        rows=[r for r in rows if evaluate(query["predicate"],r,qualifiers).value]
    aggregate=any(has_aggregate(node) for _,node in query["projection"])
    grouped=relation.grouped
    group_node=query["group"]
    if aggregate:
        if grouped or group_node is None or resolve(group_node,prototype,qualifiers).lineage!=("base","team"):
            raise Contradiction("team_grouping_not_proven")
        groups={}
        for row in rows:
            groups.setdefault(evaluate(group_node,row,qualifiers).value,[]).append(row)
        units=[(values[0],values) for values in groups.values()];grouped=True
    else:
        if group_node is not None:
            raise Contradiction("metric_lineage_not_proven")
        units=[(r,None) for r in rows]
    output=[];lineage={}
    for row,group in units:
        record={name:evaluate(node,row,qualifiers,group) for name,node in query["projection"]}
        proofs={name:cell.lineage for name,cell in record.items()}
        if lineage and lineage!=proofs:
            raise Unsupported("row_dependent_lineage")
        lineage=proofs;output.append(record)
    # ORDER BY output aliases or selected source expressions, all fully resolved.
    order_proofs=[]
    for node,direction in query["order"]:
        if node[0]!="column" or len(node[1])!=1 or node[1][0] not in lineage:
            raise Unsupported("order_expression")
        field=node[1][0];order_proofs.append((lineage[field],direction))
    full=relation.full_domain
    if query["limit"] is not None:
        if not final:
            raise Unsupported("limited_cte")
        elif query["limit"]<len(output) and (not order_proofs or order_proofs[0]!=(RATE,"desc")):
            raise Contradiction("ranking_not_proven")
    for (node,direction) in reversed(query["order"]):
        output.sort(key=lambda row:row[node[1][0]].value,reverse=direction=="desc")
    if query["limit"] is not None:
        output=output[:query["limit"]]
    return Relation(output,lineage,scope,grouped,full,bool(query["order"]),query["limit"] is not None)

def prove(sql,snapshot):
    ctes,query=Parser(sql).parse()
    lineage={"id":("base","id"),"team":("base","team"),"status":("base","status"),"blocked":B}
    rows=[{key:Cell(F(value) if type(value) is int else value,lineage[key]) for key,value in r.items() if key in lineage} for r in snapshot]
    environment={"delivery_work_items":Relation(rows,lineage)}
    for name,cte in ctes:
        environment[name]=interpret(cte,environment)
    result=interpret(query,environment,True)
    if result.scope!="active":
        raise Contradiction("wrong_population")
    if not result.full_domain:
        raise Contradiction("truncated_team_domain")
    teams=[name for name,proof in result.lineage.items() if proof==("base","team")]
    metrics=[name for name,proof in result.lineage.items() if proof==RATE]
    if not result.grouped or len(teams)!=1:
        raise Contradiction("team_lineage_not_proven")
    if len(metrics)!=1:
        raise Contradiction("metric_lineage_not_proven")
    return result,teams[0],metrics[0]
