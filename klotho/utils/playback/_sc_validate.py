"""Validate SC/SuperSonic event lists before they reach the browser scheduler.

Raises ``AssemblyValidationError`` on the first structural violation.
Call ``validate_sc_events`` on any event list destined for the SuperSonic
engine (audio-only or animation).  Call ``validate_sc_meta`` on Score meta
dicts.
"""


class AssemblyValidationError(Exception):
    pass


_VALID_EVENT_TYPES = frozenset({'new', 'set', 'release'})
_FORBIDDEN_PFIELD_KEYS = frozenset({'group', '_slur_id', '_slur_start', '_slur_end'})


def _err(idx, msg):
    raise AssemblyValidationError(f"SC event [{idx}]: {msg}")


def _check_pfields(idx, pfields, label="pfields"):
    if not isinstance(pfields, dict):
        _err(idx, f"{label} must be a dict, got {type(pfields).__name__}")
    for k, v in pfields.items():
        if not isinstance(k, str):
            _err(idx, f"{label} key must be str, got {type(k).__name__}")
        if k in _FORBIDDEN_PFIELD_KEYS:
            _err(idx, f"forbidden key '{k}' leaked into {label}")
        if not isinstance(v, (int, float)):
            _err(idx, f"{label}['{k}'] must be numeric, got {type(v).__name__}={v!r}")


def validate_sc_events(events, animation=False):
    """Validate a list of SC assembly events.

    Parameters
    ----------
    events : list[dict]
        The event list to validate.
    animation : bool
        If True, ``_stepIndex`` is expected on every non-rest ``new`` event.

    Raises
    ------
    AssemblyValidationError
        On the first invalid event.
    """
    if not isinstance(events, list):
        raise AssemblyValidationError(f"Expected list of events, got {type(events).__name__}")

    new_ids = set()
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            _err(i, f"expected dict, got {type(ev).__name__}")

        etype = ev.get('type')
        if etype not in _VALID_EVENT_TYPES:
            _err(i, f"unknown type '{etype}'")

        eid = ev.get('id')
        if not isinstance(eid, str) or not eid:
            _err(i, f"'id' must be a non-empty str, got {eid!r}")

        start = ev.get('start')
        if not isinstance(start, (int, float)):
            _err(i, f"'start' must be numeric, got {type(start).__name__}")
        if start < 0:
            _err(i, f"'start' must be >= 0, got {start}")

        if etype == 'new':
            defName = ev.get('defName')
            if not isinstance(defName, str) or not defName:
                _err(i, f"'defName' must be a non-empty str, got {defName!r}")
            if 'pfields' not in ev:
                _err(i, "'new' event missing 'pfields'")
            if defName != '__rest__':
                _check_pfields(i, ev['pfields'])
            new_ids.add(eid)
            if animation and defName != '__rest__':
                if '_stepIndex' not in ev and ev.get('_stepIndex') is None:
                    pass

        elif etype == 'set':
            if 'pfields' not in ev:
                _err(i, "'set' event missing 'pfields'")

        elif etype == 'release':
            if eid not in new_ids:
                _err(i, f"release for id '{eid[:16]}...' with no preceding 'new'")


def validate_sc_meta(meta):
    """Validate a Score meta dict.

    Parameters
    ----------
    meta : dict
        The meta dict from ``Score._build_meta()``.

    Raises
    ------
    AssemblyValidationError
        On the first invalid field.
    """
    if not isinstance(meta, dict):
        raise AssemblyValidationError(f"meta must be a dict, got {type(meta).__name__}")

    groups = meta.get('groups')
    if groups is not None:
        if not isinstance(groups, list):
            raise AssemblyValidationError(f"meta.groups must be a list, got {type(groups).__name__}")
        for g in groups:
            if not isinstance(g, str):
                raise AssemblyValidationError(f"meta.groups entry must be str, got {type(g).__name__}")

    inserts = meta.get('inserts')
    if inserts is not None:
        if not isinstance(inserts, dict):
            raise AssemblyValidationError(f"meta.inserts must be a dict, got {type(inserts).__name__}")
        for track_name, chain in inserts.items():
            if not isinstance(chain, list):
                raise AssemblyValidationError(f"meta.inserts['{track_name}'] must be a list")
            for j, spec in enumerate(chain):
                if not isinstance(spec, dict):
                    raise AssemblyValidationError(f"meta.inserts['{track_name}'][{j}] must be a dict")
                for required in ('uid', 'defName', 'args'):
                    if required not in spec:
                        raise AssemblyValidationError(f"meta.inserts['{track_name}'][{j}] missing '{required}'")
