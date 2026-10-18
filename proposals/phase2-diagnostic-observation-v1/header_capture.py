"""Inactive diagnostic-only primitive; never imported by benchmark execution.

A buffered readline may consume a partial status/header before raising timeout,
without returning those bytes. Capture each byte before requesting the next one.
The cumulative cap is shared by status and all headers; transport exceptions
propagate without retry. This does not prove a complete wire capture: bytes
buffered below this reader but never returned remain unobserved.
"""

def read_bounded_line(fp, captured, cap):
    """Return one header line while retaining returned bytes on every failure."""
    if type(cap) is not int or cap <= 0 or not isinstance(captured, bytearray):
        raise ValueError('positive integer cap and bytearray capture required')
    line = bytearray()
    while True:
        if len(captured) >= cap:
            raise RuntimeError('cumulative header limit reached')
        chunk = fp.read(1)
        if not chunk:
            if line:
                raise RuntimeError('incomplete header at EOF')
            return b''
        if not isinstance(chunk, bytes) or len(chunk) != 1:
            raise TypeError('binary reader must respect read(1)')
        captured.extend(chunk)
        line.extend(chunk)
        if chunk == b'\n':
            return bytes(line)
