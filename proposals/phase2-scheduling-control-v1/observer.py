"""Inactive, one-shot model-free scheduling diagnostic; never a benchmark entry.

Default CLI only prints the plan. --run requires a pinned clean checkout,
protocol hash and a prospectively verified resource-window receipt. No retry.
"""
from datetime import datetime, timezone
import argparse
import base64
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAP = 32768
WALL = 40
SETTINGS = {'readonly': '1', 'max_execution_time': '10', 'max_result_rows': '1000',
    'result_overflow_mode': 'break', 'max_rows_to_read': '10000',
    'max_bytes_to_read': '10485760', 'max_memory_usage': '134217728',
    'max_threads': '2', 'compile_expressions': '0'}
PROFILE = ('OSCPUWaitMicroseconds', 'OSCPUVirtualTimeMicroseconds', 'RealTimeMicroseconds',
    'UserTimeMicroseconds', 'SystemTimeMicroseconds', 'DiskReadElapsedMicroseconds',
    'OSIOWaitMicroseconds', 'ContextLockWaitMicroseconds', 'HardPageFaults', 'SoftPageFaults')
SYNTHETIC_SQL = 'SELECT sum(number * number) AS scheduling_probe, ' + ', '.join(
    "toString(getSetting('%s')) AS %s" % (key, key) for key in SETTINGS
) + ' FROM numbers(500) FORMAT JSONEachRow'
header_spec = importlib.util.spec_from_file_location('diagnostic_header_capture',
    HERE.parent / 'phase2-diagnostic-observation-v1/header_capture.py')
header_module = importlib.util.module_from_spec(header_spec)
header_spec.loader.exec_module(header_module)


def read_line(fp, captured):
    return header_module.read_bounded_line(fp, captured, 4096)


def save(out, name, data):
    limit = CAP if name in ('receipt.json', 'sha256.json') else CAP - 4096
    if len(data) + sum(p.stat().st_size for p in out.iterdir() if p.is_file()) > limit:
        raise RuntimeError('total output limit reached')
    with (out / name).open('xb') as stream:
        os.chmod(out / name, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def reserve(out, context):
    # A reference is a provenance requirement, not an automated capacity proof.
    if not isinstance(context, dict) or not isinstance(context.get('resource_window'), str) or not context['resource_window'].strip():
        raise ValueError('prospectively verified resource-window reference required')
    encoded = json.dumps(context, allow_nan=False).encode()
    if len(encoded) > 4096:
        raise ValueError('context exceeds 4 KiB')
    out.mkdir(mode=0o700)
    save(out, 'CONSUMED.json', b'{"remaining_launches":0,"retries":0}\n')
    save(out, 'resource-context.json', encoded)


def metadata_sql(query_id, start_us, end_us):
    if (not re.fullmatch(r'[A-Za-z0-9-]{1,100}', query_id) or
            type(start_us) is not int or type(end_us) is not int or
            not 0 <= start_us <= end_us <= start_us + WALL * 1000000):
        raise ValueError('exact ID and at most 40-second execution window required')
    keys = ','.join("'%s'" % key for key in PROFILE)
    settings = ','.join("'%s'" % key for key in SETTINGS)
    return ("SELECT query_id, type, query_duration_ms, read_rows, read_bytes, result_rows, result_bytes, "
        "memory_usage, thread_ids, peak_threads_usage, exception_code, "
        f"mapFilter((k,v) -> has([{keys}], k), ProfileEvents) AS ProfileEvents, "
        f"mapFilter((k,v) -> has([{settings}], k), Settings) AS Settings "
        "FROM system.query_log WHERE is_initial_query = 1 "
        f"AND query_id = '{query_id}' "
        f"AND query_start_time_microseconds >= fromUnixTimestamp64Micro({start_us}) "
        f"AND query_start_time_microseconds <= fromUnixTimestamp64Micro({end_us}) "
        "AND type IN ('QueryFinish','ExceptionWhileProcessing','ExceptionBeforeStart') "
        "ORDER BY event_time_microseconds DESC LIMIT 1 FORMAT JSONEachRow")


def interpret(rows, query_id):
    if not rows:
        return {'status': 'metadata_unavailable', 'phase2_qualified': False}
    if len(rows) != 1 or rows[0].get('query_id') != query_id:
        raise ValueError('metadata identity/cardinality differs')
    row = rows[0]
    events = row.get('ProfileEvents', {})
    if not isinstance(events, dict) or any(type(value) is not int or value < 0 for value in events.values()):
        raise ValueError('invalid profile map')
    return {'status': 'metadata_observed', 'query_duration_ms': row.get('query_duration_ms'),
        'profile_events': {key: events.get(key) for key in PROFILE},
        'missing_profile_events': [key for key in PROFILE if key not in events],
        'recorded_settings': row.get('Settings', {}), 'phase2_qualified': False,
        'interpretation': 'Thread aggregates; no wall-time percentage, speedup or causal attribution. Missing keys are unknown.'}


def sequence(exchange, query_id, unix_us):
    start = unix_us()
    probe = exchange(SYNTHETIC_SQL, query_id)
    end = unix_us()
    if (len(probe) != 1 or type(probe[0].get('scheduling_probe')) is not int or
            probe[0]['scheduling_probe'] != 41541750 or
            any(probe[0].get(key) != value for key, value in SETTINGS.items())):
        raise ValueError('synthetic result or effective settings mismatch; stop without metadata')
    metadata = exchange(metadata_sql(query_id, start, end), query_id + '-metadata')
    return {'probe': probe[0], 'metadata': interpret(metadata, query_id),
        'timeout_fixed': False, 'qualification_or_comparison': False}


def worker(out):
    # Only inherited existing credentials; never discover another endpoint or user.
    if not os.environ.get('CLICKHOUSE_USER') or not os.environ.get('CLICKHOUSE_PASSWORD'):
        raise ValueError('existing read-only credential environment unavailable')
    auth = base64.b64encode((os.environ['CLICKHOUSE_USER'] + ':' + os.environ['CLICKHOUSE_PASSWORD']).encode()).decode()
    counter = 0
    def exchange(sql, query_id):
        nonlocal counter
        counter += 1
        if counter > 2:
            raise RuntimeError('request ceiling reached')
        prefix = str(counter)
        save(out, prefix + '-send.json', json.dumps({'query_id': query_id, 'sql': sql,
            'parameters': {'default_format': 'JSONEachRow', **SETTINGS}, 'retries': 0}).encode())
        captured = bytearray()
        class Response(http.client.HTTPResponse):
            def _read_status(self):
                line = read_line(self.fp, captured).decode('iso-8859-1')
                parts = line.split(None, 2)
                if len(parts) < 2 or not parts[0].startswith('HTTP/') or not parts[1].isdigit():
                    raise http.client.BadStatusLine(line)
                return parts[0], int(parts[1]), parts[2].strip() if len(parts) == 3 else ''
        def read_headers(fp):
            lines = []
            while True:
                line = read_line(fp, captured)
                lines.append(line)
                if line in (b'\r\n', b'\n', b''):
                    return lines
        connection = http.client.HTTPConnection('127.0.0.1', 8123, timeout=15)
        connection.response_class = Response
        old = http.client._read_headers
        body = bytearray()
        http.client._read_headers = read_headers
        started = time.monotonic()
        try:
            connection.request('POST', '/?' + urllib.parse.urlencode({'default_format': 'JSONEachRow', **SETTINGS, 'query_id': query_id}),
                body=sql.encode(), headers={'Authorization': 'Basic ' + auth, 'Connection': 'close', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            save(out, prefix + '-status.json', json.dumps({'status': response.status}).encode())
            while len(body) < 4096:
                chunk = response.read1(min(1024, 4096 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            if len(body) >= 4096:
                raise RuntimeError('response body limit reached')
            if response.status != 200:
                raise RuntimeError('HTTP failure; see private captured response')
            return [json.loads(line) for line in body.splitlines() if line.strip()]
        finally:
            connection.close()
            http.client._read_headers = old
            save(out, prefix + '-headers.bin', captured)
            save(out, prefix + '-body.bin', body)
            save(out, prefix + '-elapsed.json', json.dumps({'seconds': time.monotonic() - started}).encode())
    result = sequence(exchange, 'aal-scheduling-control-v1-' + str(uuid.uuid4()), lambda: time.time_ns() // 1000)
    save(out, 'result.json', json.dumps(result, indent=2).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--expected-commit')
    parser.add_argument('--protocol-sha256')
    args = parser.parse_args()
    protocol = HERE / 'protocol.json'
    if not args.run:
        print(protocol.read_text())
        return 0
    if not all((args.context, args.out, args.expected_commit, args.protocol_sha256)):
        parser.error('run requires context, new output path, exact commit and protocol SHA256')
    if args.out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('capture must be outside pinned checkout')
    if hashlib.sha256(protocol.read_bytes()).hexdigest() != args.protocol_sha256:
        raise ValueError('protocol hash differs')
    if subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip() != args.expected_commit:
        raise ValueError('source commit differs')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=all'], cwd=ROOT, text=True).strip():
        raise ValueError('pinned checkout must be clean')
    if args.context.stat().st_size > 4096:
        raise ValueError('context exceeds 4 KiB')
    reserve(args.out, json.loads(args.context.read_text()))
    started = time.monotonic()
    termination = 'completed'
    code = 2
    try:
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', str(args.out.resolve())],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            code = process.wait(timeout=WALL)
        except subprocess.TimeoutExpired:
            process.kill()  # This observer has no subprocesses; never signal other services.
            termination = 'hard_wall_limit'
            try:
                code = process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                termination = 'observer_kill_not_confirmed'
    except OSError:
        termination = 'observer_launch_failed'
    save(args.out, 'receipt.json', json.dumps({'utc': datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds': time.monotonic() - started, 'returncode': code, 'termination': termination,
        'model_calls': 0, 'treatment_a_attempts': 0, 'remaining_launches': 0}).encode())
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file()}
    save(args.out, 'sha256.json', json.dumps(hashes, indent=2).encode())
    return code


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        # Reserved exclusively by the parent; worker failures are terminal.
        output = Path(sys.argv[2])
        try:
            if not (output / 'CONSUMED.json').is_file():
                raise ValueError('parent reservation absent')
            save(output, 'WORKER_CONSUMED.json', b'{"remaining_workers":0}\n')
            worker(output)
        except Exception as error:
            save(output, 'error.json', json.dumps({'type': type(error).__name__}).encode())
            sys.exit(2)
    else:
        sys.exit(main())
