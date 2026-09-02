import math
import numbers
from klotho.utils.ids import fast_id

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.tonos.systems.combination_product_sets import CombinationProductSet
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 110.0

# Above this a partial is, at best, inaudible.  20 kHz is the nominal top of
# human hearing AND it sits below the Nyquist frequency of every sample rate
# the engine can run at (22.05 kHz at 44.1 k, 24 kHz at 48 k), so one number
# covers both failure modes: silence above the ear, and aliasing above
# Nyquist.  The engine's actual rate belongs to the browser's AudioContext
# and is not knowable at lowering time, which is why the guard cannot key on
# Nyquist itself.
AUDIBLE_CEILING_HZ = 20000.0

KNOWN_KWARGS = frozenset({
    'dur', 'duration', 'arp', 'strum', 'dir', 'direction',
    'equaves', 'beat', 'bpm', 'mode', 'amp', 'ring_time', 'pause',
    'inst', 'loop',
})


def resolve_instrument(inst):
    """Resolve an ``inst`` playback argument to ``(defName, default_pfields, has_gate)``.

    Accepts either a SynthDef name string (exact match against the
    SuperSonic manifest, which includes any runtime-registered Supriya
    defs) or an ``Instrument`` instance carrying a ``defName`` (in
    practice a ``SynthDefInstrument``).  Path-style names are sugar for
    the underscore form (``'edm/kick'`` -> ``'edm_kick'``,
    ``'kl/saw'`` -> ``'kl_saw'``); after that transform the match is
    still exact.

    Parameters
    ----------
    inst : None, str, or Instrument
        ``None`` leaves synth selection to the caller's defaults.

    Returns
    -------
    tuple[str | None, dict, bool]
        ``(defName, default_pfields, has_gate)``.

    Raises
    ------
    ValueError
        If a string name is not registered (exact match only; no
        ``kl_``/``fd_`` prefix fallback, so user-registered names can
        never be shadowed by builtins).
    TypeError
        If given an object without a usable ``defName``.
    """
    if inst is None:
        return None, {}, True

    from klotho.thetos.instruments._shared import (
        canonical_def_name, load_ss_manifest, ss_synth_kind,
    )

    def _reject_non_inst(def_name):
        kind = ss_synth_kind(def_name)
        if kind in ('fx', 'infra'):
            what = 'an effect' if kind == 'fx' else 'an internal engine'
            raise TypeError(
                f"'{def_name}' is {what} SynthDef, not an instrument. "
                f"Effects belong in a track's insert chain "
                f"(SynthDefFX + Score.track(inserts=[...]))."
            )

    if isinstance(inst, str):
        inst = canonical_def_name(inst)
        manifest = load_ss_manifest()
        if inst not in manifest:
            available = ', '.join(sorted(manifest.keys()))
            raise ValueError(
                f"Unknown SynthDef name {inst!r}. Names must match exactly "
                f"(no prefix fallback). Available: {available}"
            )
        _reject_non_inst(inst)
        controls = dict(manifest[inst])
        return inst, controls, 'gate' in controls

    def_name = getattr(inst, 'defName', None)
    if def_name is None:
        raise TypeError(
            f"inst must be a SynthDef name string or an Instrument with a "
            f"defName (e.g. SynthDefInstrument); got {type(inst).__name__}"
        )
    _reject_non_inst(def_name)
    pfields = dict(getattr(inst, 'pfields', {}) or {})
    has_gate = bool(getattr(inst, 'has_gate', 'gate' in pfields))
    return def_name, pfields, has_gate


def freq_to_midi(freq):
    if not isinstance(freq, (int, float)) or freq <= 0:
        return 69.0
    return 69.0 + 12.0 * math.log2(freq / 440.0)


def coerce_sc_pfield_value(value):
    """Coerce a single pfield value to an SC/JSON-safe numeric type.

    ``Pitch`` lowers to its frequency; any other non-int/float
    ``numbers.Real`` (``Fraction``, NumPy scalars, ``Decimal``) lowers to
    ``float``. Tuples (poly/chord values) are coerced element-wise.
    Values that cannot be coerced pass through for validation to reject.
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, Pitch):
        return float(value.freq)
    if isinstance(value, numbers.Real):
        return float(value)
    if isinstance(value, tuple):
        return tuple(coerce_sc_pfield_value(v) for v in value)
    return value


def coerce_sc_pfield_values(pfields):
    """Coerce every value in a pfields dict via :func:`coerce_sc_pfield_value`."""
    return {k: coerce_sc_pfield_value(v) for k, v in pfields.items()}


def _merge_pfields(base, extra):
    if not extra:
        return base
    merged = dict(extra)
    merged.update(base)
    return merged


def scale_pitch_sequence(obj, equaves=1):
    if equaves == 0:
        equaves = 1
    scale_len = len(obj)
    abs_equaves = abs(equaves)
    going_up = equaves > 0

    all_pitches = []
    if going_up:
        for idx in range(abs_equaves * scale_len + 1):
            all_pitches.append(obj[idx])
        pitches_down = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_down
    else:
        for i in range(abs_equaves * scale_len + 1):
            all_pitches.append(obj[-i])
        pitches_up = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_up
    return all_pitches


_CONVERT_REGISTRY = None


def _build_convert_registry():
    """Playback-conversion dispatch table (built lazily, once).

    Each adapter wires one type's converter-handler call: the per-type
    argument selection and pause defaults live here; the engine supplies
    its converter callables in the ``handlers`` dict at dispatch time.
    MRO lookup makes subclass precedence automatic (CompositionalUnit
    before TemporalUnit; Scale/Chord/Voicing before the
    PitchCollectionBase catch-all).
    """
    from klotho.utils.dispatch_registry import TypeRegistry
    reg = TypeRegistry('playback conversion')

    @reg.register(Pitch)
    def _convert_pitch(obj, kw, handlers, inst_kw):
        return handlers['pitch'](obj, duration=kw['duration'], amp=kw['amp'],
                                 extra_pfields=kw['extra_pfields'], **inst_kw)

    @reg.register(Spectrum)
    def _convert_spectrum(obj, kw, handlers, inst_kw):
        return handlers['spectrum'](obj, duration=kw['duration'], arp=kw['arp'],
                                    strum=kw['strum'], direction=kw['direction'],
                                    amp=kw['amp'],
                                    extra_pfields=kw['extra_pfields'], **inst_kw)

    @reg.register(HarmonicTree)
    def _convert_harmonic_tree(obj, kw, handlers, inst_kw):
        """Audition a ``HarmonicTree`` as a spectrum on the convention root C4.

        The tree's content is its leaf ``harmonics`` -- the product of the
        ``factor`` values along each path from the root -- and those are the
        partial numbers that sound. (This used to read ``obj.partials``
        behind a ``hasattr`` guard; ``HarmonicTree`` has no such attribute,
        so the guard never matched and EVERY tree auditioned as the same
        hardcoded C4 stack of partials 1-5, silently and regardless of its
        content.)

        **C4 is a convention, not a derivation.** ``HarmonicTree`` is
        pitch-abstract: it models multiplicative harmonic relationships and
        carries no fundamental, so an audition has to supply one. C4
        (261.6256 Hz) is that supplied root, stated here because silently
        choosing a fundamental is exactly what produced the bug above. To
        hear the same relationships on another fundamental, build the
        ``Spectrum`` yourself: ``Spectrum(Pitch("A", 2), list(ht.harmonics))``.

        **``equave`` is deliberately NOT applied, pending a ruling.** A tree
        built with an equave also exposes ``ratios``, the harmonics reduced
        into that window (``HarmonicTree(2, (3, 5, 7), equave=2)`` has
        harmonics ``(6, 10, 14)`` and ratios ``(3/2, 5/4, 7/4)``). Whether an
        audition should sound the raw harmonics or the reduced ratios is an
        open design question, so this adapter sounds the harmonics -- the
        tree's primary data -- rather than guessing. Reducing here would also
        make the audition of a tree depend on a field that has no effect on
        ``harmonics`` itself.

        **The audition sounds ascending by partial, not in leaf order.**
        ``Spectrum`` is pitch-ordered, so this adapter's output is invariant
        under any permutation of the tree's leaves, and ``direction='d'`` is
        the explicit way to ask for the other order. That is deliberate on
        both counts: a score cannot notate "these noteheads, but in tree
        order" (a chord is a stack, and the arpeggio roll is bottom-to-top),
        and leaf order is not authorial order anyway -- ``leaf_nodes`` walks
        children in sorted node-id order while rustworkx recycles the ids of
        deleted nodes, so a leaf APPENDED to a tree can land in the middle of
        ``harmonics``. Ordering the audition by that would make what you hear
        depend on the tree's edit history.

        **Partials above** :data:`AUDIBLE_CEILING_HZ` **warn but still
        sound** -- see the guard below for why the tree, specifically, needs
        one.
        """
        harmonics = list(obj.harmonics)
        # A negative factor gives a negative harmonic, hence a negative
        # frequency, and the pitch machinery dies inside log2 with a bare
        # "math domain error". Whether an undertone -2 means the subharmonic
        # 1/2 is unsettled (see measure_partials, which keeps the sign), so
        # refuse audibly rather than invent a convention or crash opaquely.
        bad = [h for h in harmonics if not h > 0]
        if bad:
            raise ValueError(
                f"Cannot audition this HarmonicTree: leaf harmonics {bad} are "
                f"not positive, and a non-positive partial has no frequency. "
                f"Undertones (negative factors) have no settled playback "
                f"convention yet -- build a Spectrum explicitly with the "
                f"partial numbers you mean, e.g. Spectrum(Pitch('C4'), [1/2])."
            )
        fundamental = Pitch("C4")
        # A HarmonicTree's magnitudes are EMERGENT -- each leaf harmonic is
        # the PRODUCT of the factors along its path -- so nobody ever types
        # the number that goes ultrasonic.  A chain 2 -> 3 -> 5 -> 7 -> 11 is
        # five small, ordinary factors and one partial of 2310, which on C4
        # is 604 kHz.  Above AUDIBLE_CEILING_HZ such a partial is at best
        # inaudible, and above the engine's Nyquist frequency it ALIASES:
        # folded back into the audible band as a pitch with no relation to
        # the one asked for.  That is a wrong note which sounds entirely
        # plausible -- the exact failure mode this adapter's history is made
        # of -- so it gets named.
        #
        # It is named and NOT refused, and NOT clamped.  This is a spectral
        # tool; a composer who builds a deep tree may well mean it, and the
        # frequency asked for is still the frequency sent.  (The check is
        # against the convention root above: change the fundamental and the
        # ceiling lands on a different partial number.)
        over = [(h, fundamental.freq * h) for h in harmonics
                if fundamental.freq * h > AUDIBLE_CEILING_HZ]
        if over:
            import warnings
            shown = ", ".join(f"{h} ({f:.1f} Hz)" for h, f in over[:6])
            if len(over) > 6:
                shown += f", and {len(over) - 6} more"
            warnings.warn(
                f"HarmonicTree audition: {len(over)} of {len(harmonics)} leaf "
                f"harmonics sound above {AUDIBLE_CEILING_HZ:.0f} Hz on the "
                f"convention root C4 -- {shown}. Leaf harmonics are the "
                f"product of the factors along each path, so they grow much "
                f"faster than the factors do. These sound as asked and are "
                f"not clamped, but above the engine's Nyquist frequency they "
                f"alias to unrelated audible pitches. To hear the structure "
                f"instead, reduce it into an equave (HarmonicTree(..., "
                f"equave=2).ratios) or build the Spectrum yourself on a "
                f"lower fundamental.",
                UserWarning, stacklevel=2)
        spectrum = Spectrum(fundamental, harmonics)
        return _convert_spectrum(spectrum, kw, handlers, inst_kw)

    @reg.register(RhythmTree)
    def _convert_rhythm_tree(obj, kw, handlers, inst_kw):
        return handlers['rhythm_tree'](obj, beat=kw['beat'], bpm=kw['bpm'],
                                       amp=kw['amp'],
                                       extra_pfields=kw['extra_pfields'])

    @reg.register(TemporalUnitSequence)
    def _convert_temporal_sequence(obj, kw, handlers, inst_kw):
        # ``amp`` is forwarded for the same reason the TemporalUnit adapter
        # below forwards it: KNOWN_KWARGS reserves the name, so a value not
        # passed on here is not merely ignored -- it is destroyed, with no
        # unknown-kwarg error left to notice it by.
        return handlers['temporal_sequence'](obj, amp=kw['amp'],
                                             extra_pfields=kw['extra_pfields'])

    @reg.register(TemporalBlock)
    def _convert_temporal_block(obj, kw, handlers, inst_kw):
        return handlers['temporal_block'](obj, amp=kw['amp'],
                                          extra_pfields=kw['extra_pfields'])

    @reg.register(CompositionalUnit)
    def _convert_compositional_unit(obj, kw, handlers, inst_kw):
        return handlers['compositional_unit'](obj, extra_pfields=None)

    @reg.register(TemporalUnit)
    def _convert_temporal_unit(obj, kw, handlers, inst_kw):
        return handlers['temporal_unit'](obj, amp=kw['amp'],
                                         extra_pfields=kw['extra_pfields'])

    @reg.register(ChordSequence)
    def _convert_chord_sequence(obj, kw, handlers, inst_kw):
        pause = kw['pause']
        return handlers['chord_sequence'](obj, duration=kw['duration'], arp=kw['arp'],
                                          strum=kw['strum'], direction=kw['direction'],
                                          amp=kw['amp'],
                                          pause=(0.25 if pause is None else pause),
                                          extra_pfields=kw['extra_pfields'], **inst_kw)

    @reg.register(Scale)
    def _convert_scale(obj, kw, handlers, inst_kw):
        pause = kw['pause']
        return handlers['scale'](obj, duration=kw['duration'], equaves=kw['equaves'],
                                 amp=kw['amp'],
                                 pause=(0.0 if pause is None else pause),
                                 extra_pfields=kw['extra_pfields'], **inst_kw)

    @reg.register(CombinationProductSet)
    def _convert_cps(obj, kw, handlers, inst_kw):
        return _convert_scale(obj.collection, kw, handlers, inst_kw)

    @reg.register(Chord, Voicing)
    def _convert_chord(obj, kw, handlers, inst_kw):
        return handlers['chord'](obj, duration=kw['duration'], arp=kw['arp'],
                                 strum=kw['strum'], direction=kw['direction'],
                                 amp=kw['amp'],
                                 extra_pfields=kw['extra_pfields'], **inst_kw)

    @reg.register(PitchCollectionBase)
    def _convert_pitch_collection(obj, kw, handlers, inst_kw):
        pause = kw['pause']
        if kw['mode'] == "chord":
            return handlers['pitch_collection'](obj, duration=kw['duration'],
                                                mode="chord", arp=kw['arp'],
                                                strum=kw['strum'],
                                                direction=kw['direction'],
                                                amp=kw['amp'], pause=0.0,
                                                extra_pfields=kw['extra_pfields'],
                                                **inst_kw)
        return handlers['pitch_collection'](obj, duration=kw['duration'],
                                            mode="sequential", amp=kw['amp'],
                                            pause=(0.0 if pause is None else pause),
                                            extra_pfields=kw['extra_pfields'],
                                            **inst_kw)

    return reg


def dispatch_convert(obj, kwargs, handlers, include_inst=False):
    """Shared type-dispatch for the playback converters.

    A :class:`~klotho.utils.dispatch_registry.TypeRegistry` resolves the
    object's type through its MRO and calls the matching adapter, which
    wires the per-type arguments; each engine supplies its converter
    callables in ``handlers`` (keys: ``pitch``, ``spectrum``,
    ``rhythm_tree``, ``temporal_sequence``, ``temporal_block``,
    ``compositional_unit``, ``temporal_unit``, ``chord_sequence``,
    ``scale``, ``chord``, ``pitch_collection``). A new playable type is
    added by registering one adapter. ``include_inst`` forwards the
    ``inst`` kwarg for engines whose handlers support instrument
    selection (SuperSonic).
    """
    global _CONVERT_REGISTRY
    if _CONVERT_REGISTRY is None:
        _CONVERT_REGISTRY = _build_convert_registry()
    kw = extract_convert_kwargs(kwargs)
    inst_kw = {'inst': kw['inst']} if include_inst else {}
    handler = _CONVERT_REGISTRY.lookup(obj)
    if handler is None:
        raise TypeError(f"Unsupported object type: {type(obj)}")
    return handler(obj, kw, handlers, inst_kw)


def extract_convert_kwargs(kwargs):
    extra = {k: v for k, v in kwargs.items() if k not in KNOWN_KWARGS}
    return {
        'duration': kwargs.get('dur', kwargs.get('duration', None)),
        'arp': kwargs.get('arp', False),
        'mode': kwargs.get('mode', None),
        'strum': kwargs.get('strum', 0),
        'direction': kwargs.get('dir', 'u'),
        'equaves': kwargs.get('equaves', 1),
        'beat': kwargs.get('beat', None),
        'bpm': kwargs.get('bpm', None),
        'amp': kwargs.get('amp', None),
        'pause': kwargs.get('pause', None),
        'inst': kwargs.get('inst', None),
        'extra_pfields': extra if extra else None,
    }


PERC_ATTACK = 0.005
PERC_BODY_RATIO = 1 / 3


def perc_env_pfields(dur, controls=None):
    """A length-proportional percussion envelope as pfields.

    ``controls`` is the target SynthDef's declared control mapping (from
    ``load_ss_manifest()``); fields it does not declare are omitted.

    The filter is here because the bundled ``DEFAULT_RHYTHM_SYNTH``
    (``kl_kicktone``) declares none of these four names, so every bare
    rhythm note shipped four pfields that scsynth silently discarded --
    which reads, to anyone looking at the payload or at
    ``temporal_unit_to_sc_events``, as though the note's length shapes its
    envelope. It does not; ``kl_kicktone`` has its own ``bodyAtk`` /
    ``bodyDec`` / ``sustainRel`` family with its own defaults.

    It is a FILTER and not a deletion so that a rhythm synth which *does*
    declare these controls still receives them. ``controls=None`` means
    "no declaration available" and ships everything -- a runtime-registered
    def missing from the manifest must not be quietly starved of its
    envelope for a bookkeeping reason.
    """
    body = dur * PERC_BODY_RATIO
    attack = min(PERC_ATTACK, body * 0.5)
    fields = {
        "attack": attack,
        "decay": 0,
        "sustain": max(0, body - attack),
        "release": max(0, dur - body),
    }
    if controls is None:
        return fields
    return {k: v for k, v in fields.items() if k in controls}


def _is_tuple_value(value):
    return isinstance(value, tuple) and len(value) > 0


def _normalized_strum_value(raw_strum):
    if not isinstance(raw_strum, (int, float)):
        return 0.0
    return max(-1.0, min(1.0, float(raw_strum)))


def lower_poly_pfields_to_voices(pfields, voice_count=None):
    """Expand tuple pfields into per-voice pfield dicts.

    The natural voice count is the longest tuple's length (1 with no
    tuples); ``voice_count`` overrides it upward, with shorter tuples
    modulo-cycling and scalars broadcasting — used by slur groups, which
    expand every member event to the group's maximum so no voice enters
    or leaves mid-slur. The second return value reports whether the
    event itself contained tuples (force-expanded scalar events return
    ``False``, so they never strum).
    """
    tuple_fields = {k: v for k, v in pfields.items() if _is_tuple_value(v)}
    tuple_expanded = bool(tuple_fields)
    natural = max((len(v) for v in tuple_fields.values()), default=1)
    target = max(natural, voice_count) if voice_count is not None else natural
    if target == 1 and not tuple_fields:
        return [dict(pfields)], False

    expanded = []
    for voice_index in range(target):
        voice_pfields = {}
        for key, value in pfields.items():
            if key in tuple_fields:
                seq = tuple_fields[key]
                voice_pfields[key] = seq[voice_index % len(seq)]
            else:
                voice_pfields[key] = value
        expanded.append(voice_pfields)
    return expanded, tuple_expanded


def lower_event_ir_to_voice_events(event, step_index=None, voice_count=None):
    base_pfields = dict(event.pfields)
    expanded_pfields, tuple_expanded = lower_poly_pfields_to_voices(
        base_pfields, voice_count=voice_count)
    voice_count = len(expanded_pfields)
    base_start = float(event.start)
    duration = abs(float(event.duration))
    mfields = event.mfields if hasattr(event, "mfields") else {}
    strum_raw = mfields.get("strum", 0.0)
    strum_value = _normalized_strum_value(strum_raw)
    apply_strum = tuple_expanded and voice_count > 1 and strum_value != 0.0
    logical_step_id = fast_id()
    voices = []

    for voice_index, voice_pfields in enumerate(expanded_pfields):
        if apply_strum:
            order_index = voice_index if strum_value >= 0 else (voice_count - 1 - voice_index)
            start_offset = (abs(strum_value) * duration * order_index) / voice_count
            is_leader = order_index == 0
        else:
            start_offset = 0.0
            is_leader = voice_index == 0

        voices.append({
            "node_id": event.node_id,
            "start": base_start + start_offset,
            "duration": max(0.0, duration - start_offset),
            "end": (base_start + start_offset) + max(0.0, duration - start_offset),
            "pfields": voice_pfields,
            "mfields": dict(mfields),
            "step_index": step_index,
            "poly_group_id": logical_step_id,
            "logical_step_id": logical_step_id,
            "poly_voice_index": voice_index,
            "poly_voice_count": voice_count,
            "poly_is_leader": is_leader,
            "animate": bool(is_leader),
            "tuple_expanded": tuple_expanded,
        })

    return voices


def iter_group_sequence(groups, dur, arp=False, strum=0, direction='u', pause=0.0):
    current_time = 0.0
    for gi, group in enumerate(groups):
        values = list(group)
        if direction.lower() == 'd':
            values = list(reversed(values))

        if arp:
            n = len(values)
            voice_dur = dur / max(1, n)
            for i, value in enumerate(values):
                yield gi, i, current_time + i * voice_dur, voice_dur, value
        else:
            strum_val = max(0, min(1, strum))
            num = len(values)
            for i, value in enumerate(values):
                start_offset = (strum_val * dur * i) / num if num > 1 else 0
                yield gi, i, current_time + start_offset, dur - start_offset, value

        current_time += dur + max(0.0, pause)
