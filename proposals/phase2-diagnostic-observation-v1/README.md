# Inactive diagnostic partial-header capture correction v1

The preserved metadata observer timed out without returning status/header bytes.
Its buffered `readline` can consume partial input and then raise without returning
those bytes, making a zero-byte capture ambiguous. Two scripted regressions fail
on the exact legacy read/extend behavior and pass with this byte-preserving reader.
The original observer and all collected evidence remain unchanged.

This 32-line, standard-library-free helper retains every returned byte before the
next potentially blocking read, shares a cumulative cap across status/headers,
and propagates transport failures without retries. Seven offline tests cover
partial timeout/error/EOF, complete lines and cumulative limits. It is an inactive
proposal, has no network entry point and is not imported by any benchmark path.
A lower buffering layer can still hold bytes this reader never received; it is
not a packet capture or evidence that the server sent nothing.

This correction improves future diagnostic evidence only. It does not fix the
ClickHouse CPU scheduling delay, change timeouts, select a research method,
authorize another attempt, or modify the frozen runtime/tool/parser/scorer/data.
Future observer integration must retain its separate bounded authorization.
