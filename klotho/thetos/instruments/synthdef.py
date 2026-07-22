import copy

from .base import Instrument, Kit, Effect
from ._shared import (
    canonical_def_name, ss_synth_controls, load_ss_manifest, load_ss_kinds,
)


class SynthDefInstrument(Instrument):
    """A SynthDef-backed instrument.

    ``has_gate`` is a derived property: an instrument is "gated" iff its
    ``pfields`` contains a ``'gate'`` key.  There is no separate
    ``release_mode`` flag to keep in sync; if you want one-shot behavior,
    omit ``gate`` from the pfields.  The normal way to suppress per-event
    auto-release is to set ``releaseAfter=False`` on that event, not to
    mutate the instrument.

    Every *instrument* SynthDef in the bundled SuperSonic manifest is also
    available as a named classmethod constructor (e.g.
    ``SynthDefInstrument.tri()``, ``SynthDefInstrument.klank()``),
    equivalent to calling :meth:`from_manifest` with the corresponding
    defName. Effect SynthDefs get the same treatment on
    :class:`SynthDefFX` (e.g. ``SynthDefFX.reverb(mix=0.3)``).

    Parameters
    ----------
    name : str, optional
        Display name (default is ``'default'``).
    defName : str or None, optional
        SuperCollider SynthDef name. Defaults to ``'default'``.
    pfields : dict, optional
        Default parameter-field values. If omitted, a standard
        amp/freq/pan/gate/out set is used.
    """

    def __init__(self, name='default', defName=None, pfields=None):
        if pfields is None:
            pfields = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
        defName = 'default' if defName is None else defName
        super().__init__(name=name, pfields=pfields)
        self._defName = defName

    @property
    def defName(self):
        """str : The SuperCollider SynthDef name."""
        return self._defName

    @property
    def has_gate(self) -> bool:
        """bool : Whether the instrument is gated (its pfields contain ``'gate'``)."""
        return 'gate' in self._pfields

    @classmethod
    def sampler(cls, sample: str, name: str = None, **overrides):
        """Create a one-shot sample-player instrument for a bundled sample.

        Picks ``kl_sampler1`` (mono) or ``kl_sampler2`` (stereo) based on
        the sample's channel count and sets the ``buf`` pfield to the
        symbolic sample name (resolved to a bufnum by the browser
        scheduler at play time).

        By default the instrument carries a ``duration`` pfield, so the
        assembly layer injects each event's rhythmic duration and the
        synth self-frees at the event boundary (``loop=1`` repeats the
        sample until then).  Pass ``duration=None`` to drop the pfield:
        the synth then plays the remaining sample exactly once,
        regardless of the event's duration.

        Parameters
        ----------
        sample : str
            Bundled sample name (e.g. ``'bb_kick'``); see
            ``klotho.utils.playback.supersonic.samples.sample_names()``.
        name : str or None, optional
            Display name. Defaults to the sample name.
        **overrides
            Pfield values overriding the SynthDef defaults
            (``amp``, ``pan``, ``rate``, ``pos``, ``loop``, ``duration``,
            ``attackTime``, ``releaseTime``, ...).  A value of ``None``
            removes the pfield.

        Returns
        -------
        SynthDefInstrument
        """
        from klotho.utils.playback.supersonic.samples import sample_info

        info = sample_info(sample)
        def_name = 'kl_sampler2' if info['channels'] >= 2 else 'kl_sampler1'
        pfields = copy.deepcopy(ss_synth_controls(def_name))
        pfields['buf'] = sample
        pfields.update(overrides)
        pfields = {k: v for k, v in pfields.items() if v is not None}
        return cls(
            name=name or sample,
            defName=def_name,
            pfields=pfields,
        )

    @classmethod
    def from_manifest(cls, defName: str, name: str = None, **overrides):
        """Create an instrument from the bundled SuperSonic SynthDef manifest.

        Looks up the SynthDef's control names and defaults from the manifest
        and uses them as pfields.

        Parameters
        ----------
        defName : str
            SynthDef name as registered in the manifest (e.g. ``'kl_tri'``),
            or its path-style spelling (``'kl/tri'``, ``'edm/kick'``) — the
            ``/`` is replaced with ``_`` before lookup.
        name : str or None, optional
            Display name. Defaults to ``defName``.
        **overrides
            Pfield values overriding the manifest defaults.

        Returns
        -------
        SynthDefInstrument
        """
        defName = canonical_def_name(defName)
        controls = ss_synth_controls(defName)
        pfields = copy.deepcopy(controls)
        pfields.update(overrides)
        return cls(
            name=name or defName,
            defName=defName,
            pfields=pfields,
        )

    def __str__(self):
        return f"SynthDefInstrument(name='{self._name}', defName='{self._defName}', pfields={dict(self._pfields)})"


class SynthDefFX(Effect):
    """A SynthDef-backed insert effect for use in a Score track's FX chain.

    Each ``SynthDefFX`` instance represents a unique FX node.  Two instances of
    the same ``defName`` with identical args are still two distinct nodes
    (different ``uid`` values).  The Python object itself serves as the
    handle -- pass it to ``Score.track()`` to place it in a chain, and to
    ``UC.set_instrument()`` to automate its parameters.

    Parameters
    ----------
    defName : str
        SuperCollider SynthDef name (e.g. ``"__reverb"``).
    **initial_args
        Initial parameter values set on the node at creation time.
    """

    def __init__(self, defName, **initial_args):
        defName = canonical_def_name(defName)
        super().__init__(name=defName, pfields=initial_args)
        self._defName = defName

    @property
    def defName(self):
        """str : The SuperCollider SynthDef name."""
        return self._defName

    @property
    def args(self):
        """dict : Copy of the effect's parameter values."""
        return dict(self._pfields)

    def __str__(self):
        return f"SynthDefFX(defName='{self._defName}', uid='{self._uid}', args={dict(self._pfields)})"


# The six tr808 tom/conga voices share the ``tr808_tom`` SynthDef; these are
# the per-member tunings (from the original SC-808 defs, envelope times
# renormalized to audible seconds). Used by ``SynthDefKit.tr808`` and the
# ``tr808`` bundled Ensemble bank.
_TR808_TOM_TUNINGS = {
    'lowTom':   {'freq': 80,  'releaseTime': 0.74, 'sweep1': 1.25,     'sweep2': 1.125},
    'midTom':   {'freq': 120, 'releaseTime': 0.59, 'sweep1': 1.33333,  'sweep2': 1.125},
    'hiTom':    {'freq': 165, 'releaseTime': 0.41, 'sweep1': 1.333333, 'sweep2': 1.121212},
    'lowConga': {'freq': 165, 'releaseTime': 0.66, 'sweep1': 1.333333, 'sweep2': 1.121212},
    'midConga': {'freq': 250, 'releaseTime': 0.33, 'sweep1': 1.24,     'sweep2': 1.12},
    'hiConga':  {'freq': 370, 'releaseTime': 0.22, 'sweep1': 1.22972,  'sweep2': 1.08108},
}


class SynthDefKit(Kit):
    """A Kit whose members are SynthDefInstruments.

    Extends :class:`Kit` with SuperCollider-specific properties and
    a ``from_manifest`` factory.  Each member may have a different
    ``defName`` and may or may not be gated; the assembly layer resolves
    the correct member per event, so ``has_gate`` here delegates to the
    *default* member only as a display/fallback hint.

    Parameters
    ----------
    members : dict[str, SynthDefInstrument]
        Named SynthDef instruments.
    default : str or None
        Key of the default member.
    selector : str
        Pfield name for the selector (default ``'voice'``).
    """

    @property
    def defName(self):
        """str or None : SynthDef name of the default member."""
        return getattr(self._members[self._default], 'defName', None)

    @property
    def has_gate(self) -> bool:
        """bool : Whether the default member is gated (display/fallback hint)."""
        return getattr(self._members[self._default], 'has_gate', False)

    @classmethod
    def from_manifest(cls, members: dict, default=None, selector='voice',
                      families=None, **overrides):
        """Build a SynthDefKit from manifest defNames.

        Parameters
        ----------
        members : dict[str, str]
            Mapping of selector keys to SynthDef defNames.
        default : str or None
            Default selector key.
        selector : str
            Pfield name for the selector.
        families : dict[str, list[str]] or None
            Optional named groupings of selector keys.
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        built = {}
        for key, def_name in members.items():
            built[key] = SynthDefInstrument.from_manifest(def_name, name=key, **overrides)
        return cls(built, default=default, selector=selector, families=families)

    @classmethod
    def from_samples(cls, samples, default=None, selector='voice',
                     families=None, **overrides):
        """Build a SynthDefKit of one-shot sample players.

        Parameters
        ----------
        samples : list[str] or dict[str, str]
            Bundled sample names (list: each name is its own selector
            key) or a ``{selector_key: sample_name}`` mapping.
        default : str or None
            Default selector key (first key if omitted).
        selector : str
            Pfield name for the selector (default ``'voice'``).
        families : dict[str, list[str]] or None
            Optional named groupings of selector keys.
        **overrides
            Passed to ``SynthDefInstrument.sampler`` for every member.
        """
        if not isinstance(samples, dict):
            samples = {name: name for name in samples}
        built = {}
        for key, sample_name in samples.items():
            built[key] = SynthDefInstrument.sampler(sample_name, name=key, **overrides)
        return cls(built, default=default, selector=selector, families=families)

    @classmethod
    def from_sample_group(cls, group, selector='voice', families=None, **overrides):
        """Build a SynthDefKit from every bundled sample in *group*.

        Groups mirror the subfolders of the bundled sample assets
        (see ``klotho.utils.playback.supersonic.samples.sample_groups()``).
        Members are ordered as in the manifest, so integer selector
        indices are stable.
        """
        from klotho.utils.playback.supersonic.samples import sample_names

        names = sample_names(group)
        if not names:
            from klotho.utils.playback.supersonic.samples import sample_groups
            raise KeyError(
                f"Unknown sample group {group!r}. "
                f"Available: {', '.join(sample_groups())}"
            )
        return cls.from_samples(names, selector=selector, families=families, **overrides)

    @classmethod
    def beatbox(cls, selector='voice', **overrides):
        """Build the bundled beatbox Kit (8 vocal percussion samples).

        Members, in index order: ``bb_kick``, ``bb_hihat``, ``bb_snare``,
        ``bb_shake``, ``bb_big_kick``, ``bb_voice``, ``bb_snare2``,
        ``bb_openhihat``.  Select per event via the selector pfield using
        the key (``voice='bb_snare'``) or an integer index
        (``voice=2``; indices wrap mod 8, ``0`` is the default kick).

        Families: ``drums`` (bb_kick, bb_big_kick, bb_snare,
        bb_snare2), ``hats`` (bb_hihat, bb_openhihat, bb_shake),
        ``vox`` (bb_voice) -- e.g. ``kit.pick('drums')``.

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.sampler`` for every member.
        """
        return cls.from_sample_group('beatbox', selector=selector, families={
            'drums': ['bb_kick', 'bb_big_kick', 'bb_snare', 'bb_snare2'],
            'hats': ['bb_hihat', 'bb_openhihat', 'bb_shake'],
            'vox': ['bb_voice'],
        }, **overrides)

    @classmethod
    def tabla(cls, selector='voice', **overrides):
        """Build the bundled tabla Kit (14 tabla strokes).

        Members, in index order: ``tabla1`` … ``tabla4`` (open strokes),
        ``tabla_tas1`` … ``tabla_tas3``, ``tabla_te1``/``tabla_te2``/
        ``tabla_te_m``/``tabla_te_ne``, and ``tabla_tun1`` …
        ``tabla_tun3``.  Select per event via the selector pfield using
        the key or an integer index (wrapping mod 14).

        Families: ``open`` (dry open strokes), ``tas`` (long, ringing),
        ``te`` (short, dry punches), ``tun`` (low, resonant) -- e.g.
        ``kit.tas.pick()`` for a random tas stroke.

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.sampler`` for every member.
        """
        return cls.from_sample_group('tabla', selector=selector, families={
            'open': ['tabla1', 'tabla2', 'tabla3', 'tabla4'],
            'tas': ['tabla_tas1', 'tabla_tas2', 'tabla_tas3'],
            'te': ['tabla_te1', 'tabla_te2', 'tabla_te_m', 'tabla_te_ne'],
            'tun': ['tabla_tun1', 'tabla_tun2', 'tabla_tun3'],
        }, **overrides)

    @classmethod
    def edm_drums(cls, selector='voice', **overrides):
        """Build the edm kick/snare Kit (8 one-shot drums).

        Members, in index order: ``kick``, ``deepKick``, ``kickSoft``,
        ``snare``, ``snare2``, ``ghostSnare``, ``clap``, ``tom``.  Select
        per event via the selector pfield using the key
        (``voice='snare'``) or an integer index (wrapping mod 8, ``0``
        is the default kick).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'kick': 'edm/kick',
            'deepKick': 'edm/deepKick',
            'kickSoft': 'edm/kickSoft',
            'snare': 'edm/snare',
            'snare2': 'edm/snare2',
            'ghostSnare': 'edm/ghostSnare',
            'clap': 'edm/clap',
            'tom': 'edm/tom',
        }, default='kick', selector=selector, families={
            'kicks': ['kick', 'deepKick', 'kickSoft'],
            'snares': ['snare', 'snare2', 'ghostSnare', 'clap'],
        }, **overrides)

    @classmethod
    def edm_hats(cls, selector='voice', **overrides):
        """Build the edm hi-hat Kit (4 one-shot hats).

        Members, in index order: ``hat``, ``hat2``, ``hatLong``,
        ``hatShort``.  Select per event via the selector pfield using
        the key or an integer index (wrapping mod 4).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'hat': 'edm/hat',
            'hat2': 'edm/hat2',
            'hatLong': 'edm/hatLong',
            'hatShort': 'edm/hatShort',
        }, default='hat', selector=selector, **overrides)

    @classmethod
    def edm_perc(cls, selector='voice', **overrides):
        """Build the edm percussion Kit (6 one-shot perc voices).

        Members, in index order: ``woodblock``, ``clank``, ``blip``,
        ``rubber1``, ``rubber2``, ``ping``.  Select per event via the
        selector pfield using the key or an integer index (wrapping
        mod 6).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'woodblock': 'edm/woodblock',
            'clank': 'edm/clank',
            'blip': 'edm/blip',
            'rubber1': 'edm/rubber1',
            'rubber2': 'edm/rubber2',
            'ping': 'edm/ping',
        }, default='woodblock', selector=selector, **overrides)

    @classmethod
    def edm_sweeps(cls, selector='voice', **overrides):
        """Build the edm riser/sweep Kit (5 duration-driven gestures).

        Members, in index order: ``sweep``, ``chipSweep1``,
        ``chipSweep2``, ``chipSweep3``, ``revCymbal``.  Each member has
        a ``duration`` control, so the assembly layer injects the
        event's real duration automatically.  Select per event via the
        selector pfield using the key or an integer index (wrapping
        mod 5).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'sweep': 'edm/sweep',
            'chipSweep1': 'edm/chipSweep1',
            'chipSweep2': 'edm/chipSweep2',
            'chipSweep3': 'edm/chipSweep3',
            'revCymbal': 'edm/revCymbal',
        }, default='sweep', selector=selector, **overrides)

    @classmethod
    def edm_wubs(cls, selector='voice', **overrides):
        """Build the edm wub-bass Kit (3 duration-driven basses).

        Members, in index order: ``wub1``, ``wub2``, ``wub3``.  Each
        member has a ``duration`` control, so the assembly layer
        injects the event's real duration automatically.  Select per
        event via the selector pfield using the key or an integer
        index (wrapping mod 3).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'wub1': 'edm/wub1',
            'wub2': 'edm/wub2',
            'wub3': 'edm/wub3',
        }, default='wub1', selector=selector, **overrides)

    @classmethod
    def lofi_drums(cls, selector='voice', **overrides):
        """Build the lofi drum Kit (6 dusty one-shots).

        Members, in index order: ``dustKick``, ``snare``,
        ``ghostSnare``, ``rim``, ``hushHat``, ``hushHatOpen``.  Select
        per event via the selector pfield using the key or an integer
        index (wrapping mod 6, ``0`` is the default dustKick).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'dustKick': 'lofi/dustKick',
            'snare': 'lofi/snare',
            'ghostSnare': 'lofi/ghostSnare',
            'rim': 'lofi/rim',
            'hushHat': 'lofi/hushHat',
            'hushHatOpen': 'lofi/hushHatOpen',
        }, default='dustKick', selector=selector, families={
            'snares': ['snare', 'ghostSnare', 'rim'],
            'hats': ['hushHat', 'hushHatOpen'],
        }, **overrides)

    @classmethod
    def lofi_texture(cls, selector='voice', **overrides):
        """Build the lofi texture Kit (4 tape/mechanism one-shots).

        Members, in index order: ``tapePop``, ``tapeTick``,
        ``tapeSnap``, ``dustCrackle``.  Select per event via the
        selector pfield using the key or an integer index (wrapping
        mod 4).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'tapePop': 'lofi/tapePop',
            'tapeTick': 'lofi/tapeTick',
            'tapeSnap': 'lofi/tapeSnap',
            'dustCrackle': 'lofi/dustCrackle',
        }, default='tapeTick', selector=selector, **overrides)

    @classmethod
    def lofi_glitch(cls, selector='voice', **overrides):
        """Build the lofi glitch Kit (3 seed-driven one-shots).

        Members, in index order: ``zap``, ``blip``, ``burst``.  Every
        member derives its sound deterministically from its ``seed``
        pfield (same seed = same glitch), so roll through seeds per
        event to find keepers.  Select per event via the selector
        pfield using the key or an integer index (wrapping mod 3).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'zap': 'lofi/glitchZap',
            'blip': 'lofi/glitchBlip',
            'burst': 'lofi/glitchBurst',
        }, default='zap', selector=selector, **overrides)

    @classmethod
    def lofi_gestures(cls, selector='voice', **overrides):
        """Build the lofi gesture Kit (4 duration-driven swells).

        Members, in index order: ``wash``, ``cresc``, ``tapeRise``,
        ``tapeCrash``.  Each member has a ``duration`` control, so the
        assembly layer injects the event's real duration automatically.
        Select per event via the selector pfield using the key or an
        integer index (wrapping mod 4).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'wash': 'lofi/wash',
            'cresc': 'lofi/cresc',
            'tapeRise': 'lofi/tapeRise',
            'tapeCrash': 'lofi/tapeCrash',
        }, default='wash', selector=selector, **overrides)

    @classmethod
    def chip_drums(cls, selector='voice', **overrides):
        """Build the chip drum Kit (3 console-era one-shots).

        Members, in index order: ``kick`` (``chip_gridKick``), ``snare``
        (``chip_bitSnare``), ``hat`` (``chip_tickHat``).  Select per
        event via the selector pfield using the key or an integer index
        (wrapping mod 3, ``0`` is the default kick).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'kick': 'chip/gridKick',
            'snare': 'chip/bitSnare',
            'hat': 'chip/tickHat',
        }, default='kick', selector=selector, **overrides)

    @classmethod
    def chip_accent(cls, selector='voice', **overrides):
        """Build the chip accent Kit (4 pitched one-shots).

        Members, in index order: ``coinBlip``, ``blipLead``,
        ``powerArp``, ``zapDown``.  Select per event via the selector
        pfield using the key or an integer index (wrapping mod 4).

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every member.
        """
        return cls.from_manifest({
            'coinBlip': 'chip/coinBlip',
            'blipLead': 'chip/blipLead',
            'powerArp': 'chip/powerArp',
            'zapDown': 'chip/zapDown',
        }, default='coinBlip', selector=selector, **overrides)

    @classmethod
    def tr808(cls, selector='voice', **overrides):
        """Build the tr808 Kit (the 16 classic drum machine voices).

        Members, in index order: ``kick``, ``snare``, ``clap``, ``rim``,
        ``clave``, ``maracas``, ``cowbell``, ``lowTom``, ``midTom``,
        ``hiTom``, ``lowConga``, ``midConga``, ``hiConga``, ``hat``,
        ``hatOpen``, ``cymbal``.  The six tom/conga members share the
        ``tr808_tom`` SynthDef with per-member tunings.  Select per
        event via the selector pfield using the key (``voice='snare'``)
        or an integer index (wrapping mod 16, ``0`` is the default
        kick).

        Families: ``drums`` (kick, snare, clap, rim), ``toms``,
        ``congas``, ``perc`` (clave, maracas, cowbell), ``cymbals``
        (hat, hatOpen, cymbal) -- e.g. ``kit.toms.pick()``.

        Parameters
        ----------
        selector : str
            Pfield name for the selector (default ``'voice'``).
        **overrides
            Passed to ``SynthDefInstrument.from_manifest`` for every
            member (the tom/conga tunings win over ``overrides`` for
            their own pfields).
        """
        members = {}
        for key in ('kick', 'snare', 'clap', 'rim', 'clave', 'maracas', 'cowbell'):
            members[key] = SynthDefInstrument.from_manifest(
                f'tr808_{key}', name=key, **overrides)
        for key, tuning in _TR808_TOM_TUNINGS.items():
            members[key] = SynthDefInstrument.from_manifest(
                'tr808_tom', name=key, **{**overrides, **tuning})
        for key in ('hat', 'hatOpen', 'cymbal'):
            members[key] = SynthDefInstrument.from_manifest(
                f'tr808_{key}', name=key, **overrides)
        return cls(members, default='kick', selector=selector, families={
            'drums': ['kick', 'snare', 'clap', 'rim'],
            'toms': ['lowTom', 'midTom', 'hiTom'],
            'congas': ['lowConga', 'midConga', 'hiConga'],
            'perc': ['clave', 'maracas', 'cowbell'],
            'cymbals': ['hat', 'hatOpen', 'cymbal'],
        })

    def __str__(self):
        keys = list(self._members.keys())
        label = f"SynthDefKit(members={keys}, default='{self._default}', selector='{self._selector}'"
        if self._families:
            label += f", families={dict(self._families)}"
        return label + ")"


def _clean_method_name(name: str) -> str:
    cleaned = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name).strip('_')
    if not cleaned:
        return 'synth'
    if cleaned[0].isdigit():
        cleaned = f"synth_{cleaned}"
    return cleaned


def _base_method_name_for_def(def_name: str) -> str:
    if def_name == 'default':
        return 'default'
    if def_name.startswith('kl_') or def_name.startswith('fd_'):
        return _clean_method_name(def_name[3:])
    return _clean_method_name(def_name)


def _make_synth_classmethod(def_name: str, method_name: str):
    def _ctor(cls, name: str = None, **kwargs):
        return cls.from_manifest(def_name, name=name or method_name, **kwargs)
    _ctor.__name__ = method_name
    _ctor.__doc__ = (
        f"Create a SynthDefInstrument for the ``{def_name}`` SynthDef "
        f"(equivalent to ``from_manifest({def_name!r})``)."
    )
    return classmethod(_ctor)


def _make_fx_classmethod(def_name: str, method_name: str):
    def _ctor(cls, **initial_args):
        return cls(def_name, **initial_args)
    _ctor.__name__ = method_name
    _ctor.__doc__ = (
        f"Create a SynthDefFX for the ``{def_name}`` SynthDef "
        f"(equivalent to ``SynthDefFX({def_name!r}, **args)``)."
    )
    return classmethod(_ctor)


def _def_sort_key(def_name: str):
    if def_name == 'default':
        return (0, def_name)
    if def_name.startswith('kl_'):
        return (1, def_name)
    if def_name.startswith('fd_'):
        return (2, def_name)
    if def_name.startswith(('edm_', 'lofi_', 'chip_', 'tr808_')):
        return (3, def_name)
    return (4, def_name)


def _generate_shortcuts(target_cls, def_names, make_classmethod):
    """Attach a named classmethod to *target_cls* for every def name,
    resolving collisions by prefix suffixing (``_fd``/``_kl``) then
    numbering."""
    registered = set()
    for def_name in sorted(def_names, key=_def_sort_key):
        base_name = _base_method_name_for_def(def_name)
        method_name = base_name
        if hasattr(target_cls, method_name) or method_name in registered:
            if def_name.startswith('fd_'):
                method_name = f"{base_name}_fd"
            elif def_name.startswith('kl_'):
                method_name = f"{base_name}_kl"
            else:
                method_name = f"{base_name}_synth"
        suffix = 2
        while hasattr(target_cls, method_name) or method_name in registered:
            method_name = f"{base_name}_{suffix}"
            suffix += 1
        registered.add(method_name)
        setattr(target_cls, method_name, make_classmethod(def_name, method_name))


_ss_synths = load_ss_manifest()
_ss_kinds = load_ss_kinds()

_inst_defs = [n for n in _ss_synths if _ss_kinds.get(n, 'inst') == 'inst'
              and not n.startswith('__')]
_fx_defs = [n for n in _ss_synths if _ss_kinds.get(n) == 'fx']

_generate_shortcuts(SynthDefInstrument, _inst_defs, _make_synth_classmethod)
_generate_shortcuts(SynthDefFX, _fx_defs, _make_fx_classmethod)
