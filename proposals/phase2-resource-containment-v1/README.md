# RW-01 inactive resource-containment successor

The executed resource snapshot used the original sampler and supervisor while a
coordinator containment hold was still open. The executor missed the newer issue95
hold before launch. The fast swap-source denial is preserved as a valid terminal
failure; it is not evidence that timeout cleanup worked. Nothing in this proposal
changes or repeats that observation.

Original sampler SHA25693c5a4cbbcf4631e181d99e9ecf2b632ac8eea2df669c63e8addbe36c1bb58f8,
supervisor6eb73aed9108665dc1360bec51e68bf0ad30fdc4fbc8bc714199ab4682e06314,
and private archive40bd4055468f3ef3463e6713449c716a16bbb16eeb3591a6408e04ad051a61fc
remain unchanged. Reviewed diagnostic-control PR119/commit2b0a77c remains separate.

## Minimal corrected execution core

`containment.py` is an inactive replacement for the original local process-launch
and cleanup functions. It has no resource command list, live collection CLI,
credentials, model/SQL dependency or benchmark import. A future collector would
use its functions only through a separately declared versioned observation packet;
this proposal does not integrate it into the executed scripts, reopen consumed
passes, book a window, change access or launch another collection.

Only the outer supervisor creates a new session/process group. Sampler commands
inherit it. Per-command timeout/cap handling terminates only that direct child,
retains its returned bytes and uses the existing time budget for cleanup. Outer
cleanup always signals the newly owned group, including after an otherwise normal
sampler exit, and checks group disappearance within the existing0.5s confirmation
allowance. The group ID comes exclusively from the new worker, never an arbitrary
caller-supplied PID. An unresolved group never returns success.

The first-source-error sequence stops without a retry or second source. Outer12s,
per-source2s/3s and per-source byte caps remain caller-declared limits from the
original packet; no larger default is introduced. The existing8KiB capture writer
and its private provenance/seal requirements remain separate, unchanged integration
requirements. This core does not create or resize a capture.

This is local owned-group containment for the fixed non-detaching commands. It is
not a sandbox for arbitrary code that intentionally creates another session, nor
proof that killing a Docker client terminates a remote server-side process. No
Docker or other real resource command was used in validation. Any future source
and server-side execution implications require their own reviewed packet.

## Offline evidence

Two meaningful regressions fail against the original separate-session behavior:
a command/grandchild survive outer timeout; an abandoned child survives normal
worker exit. Both pass after correction, with group termination confirmed.
Synthetic processes hold locks on test-owned files; lock release establishes that
the process lifetime ended, including when a zombie PID has not yet disappeared.
No real process table, resource source or network inspection is needed. An initial
process-status oracle was denied by the environment; those errors are preserved
locally, and no access expansion or alternate system telemetry route was used.

Eight focused tests pass on each of Python3.11/3.12: the two real OS process-group
regressions, direct-command timeout with partial output, byte cap, first error,
command/worker launch failure and conservative unconfirmed-cleanup behavior.
The uncertain-group case uses scripted signaling, rather than risking an actual
unkillable process. All native processes are synthetic children created by the
tests and cleaned up in their own bounded groups or exact owned PIDs.

See `validation/receipt.json` and red/green logs. No unchanged benchmark tests,
full suite, scorer, statistical simulation, source collection, SQL or model call
was rerun. Active/frozen source, original resource sources and all historical
experiment evidence remain unchanged. Independent narrow review is pending.
