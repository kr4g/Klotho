"""
Tonalities: symbol → chord resolution over arbitrary scales and tunings.

A :class:`Tonality` maps chord symbols to concrete sonorities. It is built
entirely from Klotho scales, so it speaks just intonation, EDOs, and
arbitrary equaves uniformly. Three resolution routes coexist:

- **explicit chords** — a ``{symbol: sonority}`` vocabulary (free tone
  worlds, no parsing);
- **scale degrees** — :meth:`Tonality.degree` applies a stencil to the
  base scale *at* a degree, so the chord quality falls out of the scale
  itself (Flieder's orbit covers);
- **parsed symbols** — a parser splits a symbol into
  ``(shelf, degree, quality)``: the root comes from a named *shelf* scale
  sharing the tonic, and the quality plants another scale *on* that root
  and reads a stencil from it.

Slash symbols recurse identically for every route: ``X/Y`` resolves Y's
root, re-roots the whole tonality there, and resolves X locally — giving
secondary dominants at arbitrary depth in any tonality.

:class:`Key` is the common-practice preset: case-sensitive roman numerals
(``I ii V7 bIII viiø7 V7/V ...``) over just-intonation modal shelves.
"""

from .pitch import Pitch
from .scales import Scale
from .chords import ChordSequence, Voicing
from .utils.frequency_conversion import freq_to_midicents

__all__ = ['Tonality', 'Key', 'tonicize', 'approach', 'plain']


_MODES = {
    'ionian':     Scale.ionian,
    'dorian':     Scale.dorian,
    'phrygian':   Scale.phrygian,
    'lydian':     Scale.lydian,
    'mixolydian': Scale.mixolydian,
    'aeolian':    Scale.aeolian,
    'locrian':    Scale.locrian,
}

_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

_LETTERS = 'CDEFGAB'
_NATURAL_CENTS = {'C': 0, 'D': 200, 'E': 400, 'F': 500, 'G': 700, 'A': 900, 'B': 1100}

# fully diminished seventh: the one common-practice quality no diatonic
# mode supplies — the 7th mode of harmonic minor does
_DIM7 = lambda root: Scale.harmonic_minor(root).mode(6)


def _coerce_pitch(pitch):
    return pitch if isinstance(pitch, Pitch) else Pitch(pitch)


def _coerce_shelf(spec):
    """Normalize a shelf/quality scale spec to a callable ``root -> Scale``."""
    if isinstance(spec, Scale):     # before callable(): scales are callable
        return spec.root
    if isinstance(spec, str):
        if spec == 'dim7':
            return _DIM7
        return _MODES[spec]
    if callable(spec):
        return spec
    raise TypeError(f"can't use {spec!r} as a scale source")


def _coerce_stencil(spec):
    """An int n means the first n stacked thirds; a tuple is taken as-is."""
    if isinstance(spec, int):
        return tuple(range(0, 2 * spec, 2))
    return tuple(spec)


def parse_roman(symbol):
    """
    Split a roman-numeral symbol into its four parts.

    ``'bIII'`` → ``('b', 'U', 2, '')``; ``'viiø7'`` → ``('', 'L', 6, 'ø7')``.

    Returns
    -------
    (accidental, case, degree, suffix)
    """
    accidental, body = '', symbol
    if body and body[0] in 'b#':
        accidental, body = body[0], body[1:]
    i = 0
    while i < len(body) and body[i] in 'IViv':
        i += 1
    roman, suffix = body[:i], body[i:]
    if not roman or roman.upper() not in _NUMERALS:
        raise ValueError(f"can't read the numeral in {symbol!r}")
    case = 'U' if roman[0].isupper() else 'L'
    return accidental, case, _NUMERALS.index(roman.upper()), suffix


def plain(symbol):
    """
    Strip the quality from a roman-numeral symbol: ``'vi7'`` → ``'vi'``,
    ``'Imaj7'`` → ``'I'``, ``'bII7'`` → ``'bII'``. Slash parts are kept:
    ``'V7/vi'`` → ``'V/vi'``.
    """
    head, slash, rest = symbol.partition('/')
    accidental, case, degree, _ = parse_roman(head)
    roman = _NUMERALS[degree]
    stripped = accidental + (roman if case == 'U' else roman.lower())
    return stripped + '/' + rest if slash else stripped


class Tonality:
    """
    A mapping from chord symbols to sonorities, over any scale and tuning.

    Parameters
    ----------
    tonic : Pitch or str
        The pitch every shelf scale shares as its root.
    scale : Scale or callable, optional
        The base scale (used by :meth:`degree` and as the default shelf).
    shelves : dict, optional
        ``{name: Scale | callable | mode-name}`` — named scales on the
        tonic that supply root pitches for parsed symbols.
    qualities : dict, optional
        ``{quality_key: (scale_spec, stencil_or_size)}`` — how a parsed
        quality plants a scale on the chord root and which degrees it
        takes. ``scale_spec`` may be a mode name, Scale, or callable;
        the stencil may be an int (that many stacked thirds) or an index
        tuple.
    chords : dict, optional
        ``{symbol: Voicing | Chord | (scale_spec, stencil)}`` — explicit
        vocabulary, checked before parsing. The route for free tone
        worlds.
    functions : dict, optional
        ``{function: [(weight, symbol), ...]}`` — weighted functional
        terms (tonic/subdominant/dominant and friends). Exposed as a
        RuleSet via :meth:`interface`.
    parser : callable, optional
        ``symbol -> (shelf_name, degree, quality_key)``. When None, only
        the ``chords`` and :meth:`degree` routes are available.
    stencil : tuple of int, optional
        Default stencil for :meth:`degree`. Default ``(0, 2, 4)``.

    Examples
    --------
    A free tone world (no parser, explicit vocabulary):

    >>> hexatonic = Tonality('C4', chords={
    ...     'C':   Voicing([0, 400, 700], 'cents', reference_pitch='C4'),
    ...     'Abm': Voicing([0, 300, 700], 'cents', reference_pitch='Ab3'),
    ... })
    >>> hexatonic['Abm']
    Voicing(...)

    Common practice is the :class:`Key` preset built on this engine.
    """

    def __init__(self, tonic, scale=None, shelves=None, qualities=None,
                 chords=None, functions=None, parser=None, stencil=(0, 2, 4)):
        self._tonic = _coerce_pitch(tonic)
        self._scale_factory = _coerce_shelf(scale) if scale is not None else None
        self._shelves = {name: _coerce_shelf(spec)
                         for name, spec in (shelves or {}).items()}
        if self._scale_factory is not None and '' not in self._shelves:
            self._shelves[''] = self._scale_factory
        self._qualities = {key: (_coerce_shelf(src), _coerce_stencil(stc))
                           for key, (src, stc) in (qualities or {}).items()}
        self._chords = dict(chords or {})
        self._functions = {f: list(options) for f, options in (functions or {}).items()}
        self._parser = parser
        self._stencil = _coerce_stencil(stencil)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------
    @property
    def tonic(self):
        """Pitch : The tonic pitch."""
        return self._tonic

    @property
    def scale(self):
        """Scale or None : The base scale, rooted at the tonic."""
        if self._scale_factory is None:
            return None
        return self._scale_factory(self._tonic)

    @property
    def functions(self):
        """dict : The weighted functional terms (a copy)."""
        return {f: list(options) for f, options in self._functions.items()}

    @property
    def symbols(self):
        """tuple of str : The explicit chord vocabulary, in insertion order."""
        return tuple(self._chords)

    @property
    def chords(self):
        """dict : The explicit chord entries (a copy) — merge vocabularies
        with ``Tonality(tonic, chords={**a.chords, **b.chords})``."""
        return dict(self._chords)

    def __contains__(self, symbol):
        if symbol in self._chords:
            return True
        if self._parser is None:
            return False
        try:
            self.chord(symbol)
            return True
        except (KeyError, ValueError):
            return False

    def __repr__(self):
        parts = [f"tonic={self._tonic.pitchclass}{self._tonic.octave}"]
        if self._chords:
            parts.append(f"{len(self._chords)} chords")
        if self._parser is not None:
            parts.append('parsed symbols')
        return f"{type(self).__name__}({', '.join(parts)})"

    # ------------------------------------------------------------------
    # Re-rooting (drives slash recursion and transposition)
    # ------------------------------------------------------------------
    def rooted(self, pitch):
        """
        This tonality on a new tonic.

        Shelf, quality, and degree chords follow the tonic; explicit
        ``chords`` entries are transposed by the same interval.
        """
        pitch = _coerce_pitch(pitch)
        new = object.__new__(type(self))
        new.__dict__.update(self.__dict__)
        new._tonic = pitch
        if self._chords:
            factor = pitch.freq / self._tonic.freq
            moved = {}
            for symbol, entry in self._chords.items():
                if isinstance(entry, tuple):
                    moved[symbol] = entry
                else:
                    moved[symbol] = entry.root(Pitch.from_freq(entry.reference_pitch.freq * factor))
            new._chords = moved
        return new

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    def _split_slash(self, symbol):
        head, slash, rest = symbol.partition('/')
        if slash:
            return head, self.rooted(self.root_of(rest))
        return head, self

    def root_of(self, symbol):
        """The root Pitch of *symbol* (recursive over ``/``)."""
        head, local = self._split_slash(symbol)
        if head in local._chords:
            entry = local._chords[head]
            if isinstance(entry, tuple):
                return local._tonic
            return entry.reference_pitch
        if local._parser is None:
            raise KeyError(f"{symbol!r} is not in this tonality")
        shelf, degree, _ = local._parser(head)
        return local._shelves[shelf](local._tonic)[degree]

    def chord(self, symbol):
        """
        Resolve *symbol* to a sonority (a :class:`Voicing`).

        Explicit ``chords`` entries win; otherwise the symbol is parsed,
        its root read from the named shelf, and its quality planted on
        that root. ``X/Y`` re-roots the tonality at Y's root first.
        """
        head, local = self._split_slash(symbol)
        if head in local._chords:
            entry = local._chords[head]
            if isinstance(entry, tuple):
                source, stencil = entry
                planted = _coerce_shelf(source)(local._tonic)
                return planted[list(_coerce_stencil(stencil))].as_voicing()
            return entry
        if local._parser is None:
            raise KeyError(f"{symbol!r} is not in this tonality")
        shelf, degree, quality = local._parser(head)
        root = local._shelves[shelf](local._tonic)[degree]
        source, stencil = local._qualities[quality]
        return source(root)[list(stencil)].as_voicing()

    def __getitem__(self, symbol):
        return self.chord(symbol)

    def degree(self, index, stencil=None):
        """
        A chord built *from the base scale* at a degree.

        The stencil is applied at *index*, so the quality falls out of
        the scale itself (degree 2 of major is minor because that's what
        stacking thirds there gives).

        Parameters
        ----------
        index : int
            Zero-based scale degree (equave-cyclic).
        stencil : tuple of int, optional
            Scale-step offsets from the degree. Defaults to the
            tonality's default stencil.
        """
        if self._scale_factory is None:
            raise ValueError("this tonality has no base scale")
        stencil = self._stencil if stencil is None else _coerce_stencil(stencil)
        scale = self._scale_factory(self._tonic)
        return scale[[index + s for s in stencil]].as_voicing()

    def progression(self, symbols):
        """Resolve a sequence of symbols to a :class:`ChordSequence`."""
        return ChordSequence([self.chord(symbol) for symbol in symbols])

    def interface(self, functions=None):
        """
        The functional interface as a :class:`RuleSet`.

        Each functional term maps to weighted single-symbol options, so
        one ``rewrite()`` pass turns a word of functions into a word of
        chord symbols.

        Parameters
        ----------
        functions : dict, optional
            Override the tonality's own ``functions`` table.
        """
        from klotho.topos.formal_grammars import RuleSet

        table = functions if functions is not None else self._functions
        if not table:
            raise ValueError("this tonality has no functional terms")
        return RuleSet({f: [(w, (symbol,)) for w, symbol in options]
                        for f, options in table.items()})

    # ------------------------------------------------------------------
    # Spelling (display only; provenance-based)
    # ------------------------------------------------------------------
    def _letter_index(self):
        letter = self._tonic.pitchclass[:1].upper()
        if letter not in _LETTERS:
            return None
        return _LETTERS.index(letter)

    @staticmethod
    def _spell_pitch(pitch, letter):
        """Name *pitch* using *letter*, choosing the accidental that fits."""
        cents = freq_to_midicents(pitch.freq) - 6000.0   # C4 = 0
        pc = cents % 1200.0
        diff = pc - _NATURAL_CENTS[letter]
        if diff > 600.0:
            diff -= 1200.0
        elif diff < -600.0:
            diff += 1200.0
        steps = round(diff / 100.0)
        if abs(steps) > 2:
            return None
        accidental = '#' * steps if steps >= 0 else 'b' * -steps
        octave = int((cents - diff) // 1200) + 4
        return f"{letter}{accidental}{octave}"

    def spell(self, symbol):
        """
        Spell *symbol*'s pitches with degree-correct letter names.

        The chord-root letter comes from the tonic letter plus the
        symbol's degree; chord tones advance letters by their stencil
        steps — so a ``bIII`` of C spells E♭, not D♯, in any tuning.
        Falls back to Klotho's default (sharp) names whenever letter
        arithmetic doesn't apply (explicit chords, non-heptatonic
        shelves, unnamed tonics).
        """
        voicing = self.chord(symbol)
        fallback = ' '.join(f"{p.pitchclass}{p.octave}" for p in voicing)

        tonic_letter = self._letter_index()
        if tonic_letter is None or self._parser is None:
            return fallback
        head, local = self._split_slash(symbol)
        if head in local._chords:
            return fallback
        try:
            shelf, degree, quality = local._parser(head)
        except (KeyError, ValueError):
            return fallback
        shelf_scale = local._shelves[shelf](local._tonic)
        source, stencil = local._qualities[quality]
        planted = source(shelf_scale[degree])
        if len(shelf_scale.degrees) != 7 or len(planted.degrees) != 7:
            return fallback
        base = local._letter_index()   # for X/Y, letters count from Y's root
        if base is None:
            return fallback
        root_letter = (base + degree) % 7

        names = []
        for tone, step in zip(voicing, stencil):
            letter = _LETTERS[(root_letter + step) % 7]
            name = self._spell_pitch(tone, letter)
            if name is None:
                return fallback
            names.append(name)
        return ' '.join(names)

    def show(self, symbols):
        """Print each symbol and the pitches it becomes."""
        width = max(len(s) for s in symbols)
        for symbol in symbols:
            print(f"{symbol:>{width + 2}}  ->  {self.spell(symbol)}")


# ----------------------------------------------------------------------
# The common-practice preset
# ----------------------------------------------------------------------
class Key(Tonality):
    """
    Common-practice tonality: case-sensitive roman numerals over
    just-intonation modal shelves.

    Roots: plain numerals read the tonic scale (major or natural minor);
    ``b``-prefixed numerals read a darker parallel mode on the same tonic
    (``bIII bVI bVII`` from aeolian, ``bII`` from phrygian, ``bV`` from
    locrian); ``#IV`` reads lydian. Qualities: case picks major/minor,
    suffixes pick sevenths (``7 maj7 ø7 o o7``). Slashes recurse:
    ``V7/V/V`` works.

    In minor, uppercase ``VII`` is the subtonic (natural minor) while the
    diminished ``viio``/``viio7``/``viiø7`` sits on the leading tone
    (harmonic minor), per convention.

    Parameters
    ----------
    tonic : Pitch or str
        The key's tonic.
    mode : {'major', 'minor'}, optional
        Default is ``'major'``.
    scale : Scale or callable, optional
        Replace the tonic scale (default: JI ionian/aeolian) — the same
        theory in another tuning, e.g. a 12-EDO major scale.

    Examples
    --------
    >>> C = Key('C4')
    >>> C['V7/V']            # D F# A C
    Voicing(...)
    >>> C.spell('bIII')
    'Eb4 G4 Bb4'
    """

    #: (case, suffix) -> (planted scale, stacked thirds). Class-level, so
    #: new suffixes can be registered without editing the source:
    #: ``Key.QUALITIES[('U', 'sus4')] = ('mixolydian', (0, 3, 4))``
    QUALITIES = {
        ('U', ''):     ('ionian', 3),
        ('L', ''):     ('aeolian', 3),
        ('U', '7'):    ('mixolydian', 4),
        ('L', '7'):    ('aeolian', 4),
        ('U', 'maj7'): ('ionian', 4),
        ('L', 'ø7'):   ('locrian', 4),
        ('L', 'o'):    ('locrian', 3),
        ('L', 'o7'):   ('dim7', 4),
    }

    FLAT_ROOTS = {1: 'phrygian', 2: 'aeolian', 4: 'locrian', 5: 'aeolian', 6: 'aeolian'}
    SHARP_ROOTS = {3: 'lydian'}

    FUNCTIONS = {
        'major': {
            't': [(4, 'I'), (1, 'vi')],
            's': [(3, 'IV'), (2, 'ii')],
            'd': [(4, 'V7'), (1, 'viio')],
        },
        'minor': {
            't': [(4, 'i'), (1, 'VI')],
            's': [(3, 'iv'), (2, 'iio')],
            'd': [(4, 'V7'), (1, 'viio')],
        },
    }

    def __init__(self, tonic, mode='major', scale=None, functions=None):
        if mode not in ('major', 'minor'):
            raise ValueError("mode must be 'major' or 'minor'")
        self._mode = mode
        if scale is None:
            scale = Scale.ionian if mode == 'major' else Scale.aeolian
        shelves = dict(_MODES)
        shelves['leading'] = Scale.harmonic_minor   # viio-in-minor root source
        shelves['tonic'] = _coerce_shelf(scale)
        super().__init__(
            tonic, scale=scale, shelves=shelves,
            qualities=dict(type(self).QUALITIES),
            functions=functions if functions is not None else type(self).FUNCTIONS[mode],
            parser=self._parse, stencil=(0, 2, 4),
        )

    @property
    def mode(self):
        """str : ``'major'`` or ``'minor'``."""
        return self._mode

    def _parse(self, symbol):
        accidental, case, degree, suffix = parse_roman(symbol)
        if (case, suffix) not in self._qualities:
            raise KeyError(f"unknown chord quality {suffix!r} in {symbol!r}")
        if accidental == 'b':
            shelf = type(self).FLAT_ROOTS[degree]
        elif accidental == '#':
            shelf = type(self).SHARP_ROOTS[degree]
        elif (self._mode == 'minor' and degree == 6 and case == 'L'
              and suffix in ('o', 'o7', 'ø7', '')):
            shelf = 'leading'   # viio in minor sits on the raised 7th
        else:
            shelf = 'tonic'
        return shelf, degree, (case, suffix)


# ----------------------------------------------------------------------
# Word-level transforms (Rohrmeier's scale-degree rules)
# ----------------------------------------------------------------------
def _coerce_rng(rng):
    import random as _random
    if rng is None or rng is _random:
        return _random
    if isinstance(rng, _random.Random):
        return rng
    return _random.Random(rng)


def tonicize(symbols, probability, dominant='V7', skip=('I', 'i'), rng=None):
    """
    Sprinkle applied dominants over a progression (rule ``X → D(X) X``).

    Each symbol (except those in *skip*) is preceded, with the given
    probability, by ``dominant + '/' + plain(symbol)``. One pass, no
    recursion — nested dominants come from nesting slashes in *dominant*.

    Parameters
    ----------
    symbols : sequence of str
        The progression, as roman-numeral symbols.
    probability : float
        Per-symbol chance of sprouting its dominant.
    dominant : str, optional
        The applied chord. ``'V7'`` (default), ``'viio7'``, ...
    skip : tuple of str, optional
        Symbols never tonicized (default: the tonic).
    rng : random.Random or int, optional
        Source of randomness (or a seed).
    """
    rng = _coerce_rng(rng)
    out = []
    for symbol in symbols:
        if symbol not in skip and rng.random() < probability:
            out.append(dominant + '/' + plain(symbol))
        out.append(symbol)
    return out


def approach(symbols, probability, with_=('ii7', 'V7'), tritone=0.0, rng=None):
    """
    Precede symbols with their approach chords (the ii–V machine).

    Each symbol is preceded, with the given probability, by the chords in
    *with_* applied to it (``ii7/X V7/X X``). When the last approach
    chord is a dominant, *tritone* is the chance it is swapped for its
    tritone substitute ``bII7/X``.

    Parameters
    ----------
    symbols : sequence of str
        The progression, as roman-numeral symbols.
    probability : float
        Per-symbol chance of being approached.
    with_ : tuple of str, optional
        The approach chords, nearest last. Default ``('ii7', 'V7')``.
    tritone : float, optional
        Chance of tritone-substituting the final approach chord.
    rng : random.Random or int, optional
        Source of randomness (or a seed).
    """
    rng = _coerce_rng(rng)
    out = []
    for symbol in symbols:
        if rng.random() < probability:
            target = plain(symbol)
            chain = [f"{a}/{target}" for a in with_]
            if chain and tritone > 0 and rng.random() < tritone:
                chain[-1] = f"bII7/{target}"
            out.extend(chain)
        out.append(symbol)
    return out
