"""Fast process-unique id generation for lowering/payload paths.

``uuid4().hex`` costs ~2us per call and the lowering paths minted 2-3
ids per event. A single random 16-hex process prefix plus a monotonically
increasing 16-hex counter is ~50x cheaper and equally unique: ids cannot
collide within a process (shared counter) and collide across processes
only with uuid4-grade probability (random prefix). The result is 32 hex
chars — the same shape as ``uuid4().hex`` — so downstream consumers and
normalizers are unaffected. The JS scheduler treats ids as opaque
strings.
"""
from itertools import count
from uuid import uuid4

_PREFIX = uuid4().hex[:16]
_COUNTER = count()


def fast_id() -> str:
    """Return a process-unique 32-char lowercase hex id."""
    return _PREFIX + format(next(_COUNTER), '016x')
