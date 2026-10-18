"""Inactive local-process containment successor. No live resource collection CLI.

Only run_owned_worker creates a session. Every sampler command inherits it.
Per-command cleanup signals its direct child; outer cleanup always terminates
and checks the entire newly owned group, even after normal sampler exit.
"""
import os
import selectors
import signal
import subprocess
import time


def bounded_process(argv, seconds, cap):
    if type(cap) is not int or cap <= 0 or seconds <= 0:
        raise ValueError('positive declared time and output limits required')
    start = time.monotonic()
    deadline = start + seconds
    # Reserve part of the existing limit for direct-child cleanup; do not extend it.
    read_deadline = deadline - min(.5, seconds / 4)
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return {'stdout': b'', 'stderr': b'', 'returncode': None,
                'termination': 'launch_failed', 'elapsed_seconds': time.monotonic() - start}
    selector = selectors.DefaultSelector()
    data = {'stdout': bytearray(), 'stderr': bytearray()}
    reason = 'completed'
    code = None
    try:
        for name, stream in [('stdout', process.stdout), ('stderr', process.stderr)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = read_deadline - time.monotonic()
            if remaining <= 0:
                reason = 'time_limit'
                break
            for key, _ in selector.select(min(.05, remaining)):
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                used = sum(map(len, data.values()))
                data[key.data].extend(chunk[:cap - used])
                if sum(map(len, data.values())) >= cap:
                    reason = 'output_limit'
                    break
            if reason != 'completed':
                break
        if reason != 'completed':
            try:
                process.kill()  # Never signal the sampler's shared group here.
            except ProcessLookupError:
                pass
        try:
            code = process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            reason = 'time_limit_cleanup_unconfirmed'
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return {'stdout': bytes(data['stdout']), 'stderr': bytes(data['stderr']),
            'returncode': code, 'termination': reason, 'elapsed_seconds': time.monotonic() - start}


def run_owned_worker(argv, seconds):
    if seconds <= 0:
        raise ValueError('positive declared outer limit required')
    start = time.monotonic()
    try:
        process = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return {'state': 'launch_failed', 'returncode': None,
                'group_termination_confirmed': True, 'success': False}
    state = 'completed'
    code = None
    confirmed = False
    try:
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            state = 'time_limit'
    finally:
        # The group ID comes only from this newly created worker, never a caller.
        if process.pid == os.getpgrp():
            raise RuntimeError('refuse to signal the caller group')
        cleanup_deadline = time.monotonic() + .5
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            confirmed = True
        try:
            code = process.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
        while not confirmed and time.monotonic() < cleanup_deadline:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                confirmed = True
                break
            time.sleep(min(.01, max(0, cleanup_deadline - time.monotonic())))
    return {'state': state, 'returncode': code, 'group_termination_confirmed': confirmed,
            'success': state == 'completed' and code == 0 and confirmed,
            'elapsed_seconds': time.monotonic() - start}


def collect_sources(commands):
    """Inactive source sequence core; first failure/cap/timeout consumes the pass."""
    records = []
    started = time.monotonic()
    for command in commands:
        remaining = 12 - (time.monotonic() - started)
        if remaining <= 0:
            return records, 'total_time_limit'
        result = bounded_process(command['argv'], min(command['seconds'], remaining), command['cap'])
        records.append(result)
        if result['returncode'] != 0 or result['termination'] != 'completed':
            return records, 'stopped_at_first_failed_source'
    return records, 'complete'
