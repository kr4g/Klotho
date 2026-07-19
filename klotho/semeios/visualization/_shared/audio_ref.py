DEFAULT_REF_FREQ = 261.63


def reference_freq(obj, default=DEFAULT_REF_FREQ):
    """Frequency anchoring *obj*'s ratios in plot playback and click-to-hear.

    Lattice-family objects (``CombinationProductSet``, ``ToneLattice``,
    ``MasterSet``) carry a ``reference_pitch`` (default C4, overridable via
    ``.root()``); anything else falls back to the C4 default.
    """
    ref = getattr(obj, 'reference_pitch', None)
    if ref is None:
        return default
    try:
        return float(ref.freq)
    except (AttributeError, TypeError, ValueError):
        return default
