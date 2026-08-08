"""Fast process-unique id generation for lowering/payload paths.

``uuid4().hex`` costs ~2us per call and the lowering paths minted 2-3
ids per event. A random 8-hex process prefix plus a monotonically
increasing 8-hex counter is ~50x cheaper and process-unique: ids cannot
collide within a process (shared counter; 4.3B ids before wraparound)
and collide across processes only when two kernels draw the same 32-bit
prefix AND overlap in counter range. Events carry three ids each, so the
short shape is also a payload-size win (~48 bytes/event). The JS
scheduler treats ids as opaque strings; the payload-oracle normalizer
knows this quote-bounded 16-hex shape.
"""
from itertools import count
from uuid import uuid4

_PREFIX = uuid4().hex[:8]
_COUNTER = count()


def fast_id() -> str:
    """Return a process-unique 16-char lowercase hex id."""
    return _PREFIX + format(next(_COUNTER), '08x')
