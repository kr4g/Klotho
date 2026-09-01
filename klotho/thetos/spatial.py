"""Speaker arrays: where the music comes out.

An :class:`Ensemble` says who plays; a :class:`SpeakerArray` says where the
sound arrives.  Both are declarative value types consumed at lowering, and
neither is graph-backed.

This module is the **single source of truth for speaker positions**.  Two
consumers read the same numbers and therefore agree by construction:

* the real-time SuperCollider binaural decoder, which reads
  :meth:`SpeakerArray.binaural_coefficients` out of a control buffer, and
* the offline stereo fold, which applies the identical delays, gains and
  head-shadow cutoffs to a finished multichannel file.

Speakers are addressed by the **label the rig carries** (``1``..``24``,
``'FL'``, ...), never by a lane index.  A physical array is labelled, Klotho
is 0-based, and guessing between the two is an off-by-one that puts a sound
fifty feet from where it was written.  The label-to-lane map exists but is
never the thing a composer types.

Float, not Fraction -- and why
------------------------------
Klotho stores rhythm as :class:`~fractions.Fraction` because that arithmetic
is *closed* over the rationals: a duration divided by a tuplet is still an
exact rational.  Speaker geometry is not.  The distance between two speakers
50 ft and 60 ft apart is ``sqrt(6100)``, irrational; every propagation delay
is that irrational number divided by the speed of sound.  A rational position
would stay exact only until the first :meth:`SpeakerArray.distance` call and
then lose it anyway, while making every downstream conversion noisier.  The
consumers settle it: a SuperCollider control buffer holds 32-bit floats, and
a delay line quantizes to samples, so the last honest digit is about
1/48000 s.  Positions given as ``int`` or ``Fraction`` are therefore
converted once, at construction, with ``float()`` -- so equality and hashing
are well defined and a stored array reproduces exactly.

What is deliberately NOT here
-----------------------------
* **Choreography.**  Named regions, partitions, mirror orbits, knight
  neighbourhoods -- a venue's own map -- belong to the piece, not to Klotho.
  What is here is the general primitive: positions, distances, delays, and
  two orderings derived from the grid itself.
* **The other folds.**  The stereo (column-to-pan) and mono (delay-and-sum)
  folds are separate models with their own constants; only the binaural one
  is shared with the live decoder, so only it lives here.
* **HRTF.**  :meth:`SpeakerArray.binaural_coefficients` is *binaural-lite*:
  interaural time difference, interaural level difference, and a one-pole
  head shadow, on the left-right axis only.  No pinna filtering, so no
  front/back disambiguation.  That limitation is deliberate and is stated
  again on the method.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping, Optional, Sequence, Union

# Conventional dry-air speeds, in each unit per second. 1125 ft/s is the
# value the Sonic Pavilion geometry is quoted against.
SPEED_OF_SOUND = {'ft': 1125.0, 'm': 343.0}

# Half the interaural distance -- a human head is about 7 in across.
# 0.29 ft is the reference value; the metric entry is that, converted.
HEAD_HALF = {'ft': 0.29, 'm': 0.0884}
HEAD_HALF_FT = HEAD_HALF['ft']

# The far ear's one-pole cutoff at full shadow, and its cutoff at none.
SHADOW_LO_HZ = 1400.0
SHADOW_HI_HZ = 18000.0

# Which way the virtual listener faces. 'north' puts the x axis on
# left/right, which is the right choice when travel runs along x.
FACINGS = ('north', 'east')

# Grid label conventions. 'column-major' is the Sonic Pavilion's: the label
# advances up a column before stepping to the next column.
NUMBERINGS = ('column-major', 'row-major',
              'column-major-serpentine', 'row-major-serpentine')

START_CORNERS = ('sw', 'nw', 'se', 'ne')

# The order of the six coefficients per speaker in the flat buffer. A
# SuperCollider decoder indexes ``lane * BINAURAL_STRIDE + field``.
BINAURAL_FIELDS = ('delay_l', 'delay_r', 'gain_l', 'gain_r',
                   'shadow_l_hz', 'shadow_r_hz')
BINAURAL_STRIDE = len(BINAURAL_FIELDS)

# The live decoder's delay line, in seconds. Pass it as ``max_delay`` to
# refuse a listener the decoder could not reach; the offline fold has no
# such limit and passes nothing.
DECODER_MAX_DELAY_S = 0.5

Label = Union[int, str]
Point = Sequence[float]

__all__ = [
    'SpeakerArray',
    'BinauralCoefficients',
    'BINAURAL_FIELDS',
    'BINAURAL_STRIDE',
    'DECODER_MAX_DELAY_S',
    'FACINGS',
    'HEAD_HALF',
    'HEAD_HALF_FT',
    'NUMBERINGS',
    'SHADOW_HI_HZ',
    'SHADOW_LO_HZ',
    'SPEED_OF_SOUND',
    'START_CORNERS',
]


# ----------------------------------------------------------------------
# helpers


def _is_label(value) -> bool:
    """True for something addressable as a speaker label.

    ``bool`` is excluded on purpose: ``True`` is an ``int`` in Python, so a
    boolean label would silently collide with speaker 1.
    """
    return isinstance(value, str) or (isinstance(value, int)
                                      and not isinstance(value, bool))


def _as_float(value, what: str) -> float:
    if isinstance(value, bool):
        raise TypeError(
            f"{what} must be a real number, got {value!r} (bool).")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise TypeError(
            f"{what} must be a real number, got {value!r} "
            f"({type(value).__name__}). Positions are floats: see the module "
            "docstring for why speaker geometry is not exact arithmetic."
        ) from None


def _coerce_point(value, what: str) -> tuple:
    """A sequence of coordinates as a tuple of floats.

    Deliberately duck-typed rather than an ``isinstance(..., Sequence)``
    check: a numpy array is not a ``Sequence``, and refusing one would be a
    surprise in a package that already depends on numpy.  A string is
    refused explicitly, because iterating one gives characters.
    """
    if isinstance(value, str) or isinstance(value, (bytes, bytearray)):
        raise TypeError(
            f"{what} must be a sequence of coordinates, got {value!r}. "
            "Write (x, y) -- or (x, y, z) for a rig with height.")
    try:
        items = list(value)
    except TypeError:
        raise TypeError(
            f"{what} must be a sequence of coordinates, got {value!r} "
            f"({type(value).__name__}). Write (x, y) -- or (x, y, z) for a "
            "rig with height.") from None
    return tuple(_as_float(v, f"{what} coordinate") for v in items)


def _format_labels(labels: Sequence[Label], limit: int = 12) -> str:
    """Labels for an error message, truncated when there are many."""
    if len(labels) <= limit:
        return ', '.join(repr(x) for x in labels)
    head = ', '.join(repr(x) for x in labels[:4])
    return f"{head}, ... , {labels[-1]!r} ({len(labels)} in all)"


def _grid_cells(cols: int, rows: int, numbering: str):
    """``(col, row)`` for every lane, in label order.

    One function decides the numbering convention, and both
    :meth:`SpeakerArray.grid` (which builds the labels) and
    :meth:`SpeakerArray.serpentine` (which inverts them) go through it, so
    the two can never drift apart.
    """
    if numbering == 'column-major':
        return tuple((c, r) for c in range(cols) for r in range(rows))
    if numbering == 'row-major':
        return tuple((c, r) for r in range(rows) for c in range(cols))
    if numbering == 'column-major-serpentine':
        out = []
        for c in range(cols):
            seq = range(rows) if c % 2 == 0 else range(rows - 1, -1, -1)
            out.extend((c, r) for r in seq)
        return tuple(out)
    if numbering == 'row-major-serpentine':
        out = []
        for r in range(rows):
            seq = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)
            out.extend((c, r) for c in seq)
        return tuple(out)
    raise ValueError(
        f"unknown numbering {numbering!r}; known conventions are "
        f"{', '.join(repr(n) for n in NUMBERINGS)}. 'column-major' numbers "
        "the first column bottom to top, then steps to the next column -- "
        "the Sonic Pavilion convention.")


@dataclass(frozen=True)
class BinauralCoefficients:
    """Per-speaker delay, gain and head-shadow cutoff for each ear.

    Pure geometry -- no HRTF, no measurement.  Six numbers per speaker, in
    lane order, produced by :meth:`SpeakerArray.binaural_coefficients` and
    consumed both by the live SuperCollider decoder and by the offline fold.

    Attributes
    ----------
    labels : tuple
        The array's speaker labels, in lane order.  ``labels[i]`` names the
        speaker whose coefficients are at index ``i`` of every tuple below.
    delay_l, delay_r : tuple of float or int
        Propagation delay from the speaker to each ear.  Seconds, unless
        ``sample_rate`` was given, in which case integer sample offsets.
    gain_l, gain_r : tuple of float
        Linear amplitude, inverse-distance, normalized so the near ear is
        exactly ``1.0``.
    shadow_l_hz, shadow_r_hz : tuple of float
        One-pole lowpass cutoff for that ear, in Hz.  ``SHADOW_HI_HZ`` when
        the ear is not shadowed, falling to ``SHADOW_LO_HZ`` at a full head
        width of extra path length.
    listener : tuple of float
        The listener point these were computed for.
    facing : str
        ``'north'`` or ``'east'``; see :meth:`SpeakerArray.binaural_coefficients`.
    head_half : float
        Half the interaural distance, in the array's units.
    sample_rate : int or None
        The rate the delays were quantized to, or ``None`` for seconds.
    """

    labels: tuple
    delay_l: tuple
    delay_r: tuple
    gain_l: tuple
    gain_r: tuple
    shadow_l_hz: tuple
    shadow_r_hz: tuple
    listener: tuple
    facing: str
    head_half: float
    sample_rate: Optional[int]

    def __len__(self):
        return len(self.labels)

    def flat(self) -> tuple:
        """The coefficients as one flat tuple, ready for a control buffer.

        Layout, which a SuperCollider decoder indexes by hand::

            index = lane * 6 + field        # stride 6, lane-major

            field 0  delay_l      seconds (integer samples if sample_rate given)
            field 1  delay_r      seconds
            field 2  gain_l       linear amplitude, 1.0 at the near ear
            field 3  gain_r       linear amplitude
            field 4  shadow_l_hz  one-pole lowpass cutoff, Hz
            field 5  shadow_r_hz  one-pole lowpass cutoff, Hz

        ``lane`` is the speaker's position in :attr:`labels` -- that is,
        ``array.lane(label)`` -- and **not** the label itself.  The buffer
        is ``6 * n`` floats long for an array of ``n`` speakers; the field
        order is :data:`BINAURAL_FIELDS` and the stride is
        :data:`BINAURAL_STRIDE`, so a decoder can be generated from those
        constants rather than from a literal 6.

        Returns
        -------
        tuple of float
            ``6 * len(self)`` values.
        """
        out = []
        for i in range(len(self.labels)):
            out.extend((float(self.delay_l[i]), float(self.delay_r[i]),
                        float(self.gain_l[i]), float(self.gain_r[i]),
                        float(self.shadow_l_hz[i]), float(self.shadow_r_hz[i])))
        return tuple(out)

    def max_delay(self) -> float:
        """The longest single ear delay, in whatever unit the delays carry."""
        return max(max(self.delay_l), max(self.delay_r))


class SpeakerArray:
    """An immutable, labelled set of speaker positions with a speed of sound.

    A value type: two arrays with the same labels, positions, units, speed
    of sound, name and grid provenance are equal and hash alike.  It is
    iterable over its **labels**, ``len()``-able, and subscriptable by label
    (``array[17]`` is the position of speaker 17, not of lane 17).

    Parameters
    ----------
    positions : mapping or iterable of pairs
        ``{label: position}`` or ``[(label, position), ...]``.  Labels are
        ``int`` or ``str``; a position is a sequence of 1 to 3 numbers and
        every position must have the same length.  Insertion order is lane
        order.
    units : str, optional
        The unit positions are measured in (default ``'ft'``).  ``'ft'`` and
        ``'m'`` carry default speeds of sound and head sizes; any other unit
        is allowed but then *speed_of_sound* must be given.
    speed_of_sound : float, optional
        Propagation speed in *units* per second.  Defaults to the value for
        *units* (1125.0 ft/s, 343.0 m/s).
    name : str, optional
        A name for error messages and ``repr`` (e.g. ``'PAVILION'``).

    Raises
    ------
    ValueError
        For an empty array, duplicate labels, mixed position dimensions, a
        non-positive speed of sound, or an unknown unit with no speed given.
    TypeError
        For a label that is not an ``int`` or ``str``, or a coordinate that
        is not a real number.

    Examples
    --------
    >>> pav = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
    ...                         row_spacing=60.0, name='PAVILION')
    >>> pav.position(1), pav.position(24)
    ((0.0, 0.0), (250.0, 180.0))
    >>> pav.centre
    (125.0, 90.0)
    >>> round(pav.delay(1, 5), 6)
    0.044444
    """

    __slots__ = ('_labels', '_positions', '_lane', '_units', '_speed',
                 '_name', '_grid_shape', '_numbering')

    def __init__(self,
                 positions: Union[Mapping[Label, Point],
                                  Iterable[tuple]],
                 *,
                 units: str = 'ft',
                 speed_of_sound: Optional[float] = None,
                 name: Optional[str] = None,
                 _grid_shape: Optional[tuple] = None,
                 _numbering: Optional[str] = None):
        if isinstance(positions, (int, float, Fraction)) \
                and not isinstance(positions, bool):
            raise ValueError(
                f"speakers={positions!r} is ambiguous: Klotho will not guess "
                "whether your speakers are labelled 0..n-1 or 1..n, nor where "
                "they are. Pass labelled positions "
                "(SpeakerArray.from_positions({1: (0.0, 0.0), ...})) or build "
                "a grid (SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0, "
                "row_spacing=60.0)).")
        if not isinstance(units, str) or not units:
            raise TypeError(
                f"units must be a non-empty string, got {units!r}; "
                f"{', '.join(repr(u) for u in SPEED_OF_SOUND)} carry default "
                "speeds of sound, any other unit needs speed_of_sound=.")

        pairs = list(positions.items()) if isinstance(positions, Mapping) \
            else [tuple(p) for p in positions]

        labels, points, lane = [], [], {}
        dim = None
        for entry in pairs:
            if len(entry) != 2:
                raise ValueError(
                    f"expected (label, position) pairs, got {entry!r}. Pass a "
                    "mapping {label: (x, y)} or a list of two-element pairs.")
            label, raw = entry
            if not _is_label(label):
                raise TypeError(
                    f"speaker label {label!r} must be an int or a str, not "
                    f"{type(label).__name__}. Rigs are labelled 1..24 or "
                    "'FL'/'FR'; a float or a bool cannot name a speaker.")
            if label in lane:
                raise ValueError(
                    f"speaker label {label!r} appears twice. Every speaker "
                    "needs its own label -- a repeated label would make "
                    "position() and lane() answer for whichever one happened "
                    "to be stored last.")
            point = _coerce_point(raw, f"position for speaker {label!r}")
            if not 1 <= len(point) <= 3:
                raise ValueError(
                    f"speaker {label!r} has {len(point)} coordinates; a "
                    "position is 1-D, 2-D or 3-D. Write (x, y) for a flat "
                    "rig, (x, y, z) for one with height.")
            if dim is None:
                dim = len(point)
            elif len(point) != dim:
                raise ValueError(
                    f"speaker {label!r} has {len(point)} coordinates but "
                    f"speaker {labels[0]!r} has {dim}. Every speaker in one "
                    "array must be measured in the same number of "
                    "dimensions -- pad the flat ones with z=0.0 rather than "
                    "mixing 2-D and 3-D.")
            lane[label] = len(labels)
            labels.append(label)
            points.append(point)

        if not labels:
            raise ValueError(
                "a SpeakerArray needs at least one speaker; an empty array "
                "has no lanes to route to and no geometry to fold. Pass "
                "positions, e.g. SpeakerArray.from_positions({1: (0.0, 0.0)}).")

        if speed_of_sound is None:
            if units not in SPEED_OF_SOUND:
                raise ValueError(
                    f"units={units!r} has no default speed of sound. Pass "
                    f"speed_of_sound= in {units} per second, or use one of "
                    f"{', '.join(repr(u) for u in SPEED_OF_SOUND)}.")
            speed = SPEED_OF_SOUND[units]
        else:
            speed = _as_float(speed_of_sound, 'speed_of_sound')
            if speed <= 0.0:
                raise ValueError(
                    f"speed_of_sound={speed_of_sound!r} must be positive: it "
                    "divides every distance to give a propagation delay, so "
                    f"zero or less has no meaning. Sound travels "
                    f"{SPEED_OF_SOUND['ft']} ft/s or "
                    f"{SPEED_OF_SOUND['m']} m/s in air.")

        object.__setattr__(self, '_labels', tuple(labels))
        object.__setattr__(self, '_positions', tuple(points))
        object.__setattr__(self, '_lane', lane)
        object.__setattr__(self, '_units', units)
        object.__setattr__(self, '_speed', speed)
        object.__setattr__(self, '_name', None if name is None else str(name))
        object.__setattr__(self, '_grid_shape',
                           None if _grid_shape is None else tuple(_grid_shape))
        object.__setattr__(self, '_numbering', _numbering)

    # ------------------------------------------------------------------
    # constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_positions(cls,
                       positions: Union[Mapping[Label, Point],
                                        Iterable[tuple]],
                       *,
                       units: str = 'ft',
                       speed_of_sound: Optional[float] = None,
                       name: Optional[str] = None) -> 'SpeakerArray':
        """Build an array from arbitrary labelled positions, any dimension.

        The general constructor, and the reason this type is not specific to
        one venue: a ring, a dome, a hung 3-D rig or four corners of a room
        are all expressible.  Ordering helpers that need columns and rows
        (:meth:`serpentine`) refuse on an array built this way, because there
        are none.

        Parameters
        ----------
        positions : mapping or iterable of pairs
            ``{label: position}`` or ``[(label, position), ...]``.
        units, speed_of_sound, name
            As for :class:`SpeakerArray`.

        Returns
        -------
        SpeakerArray

        Examples
        --------
        >>> quad = SpeakerArray.from_positions(
        ...     {'FL': (-5.0, 5.0), 'FR': (5.0, 5.0),
        ...      'RL': (-5.0, -5.0), 'RR': (5.0, -5.0)})
        >>> len(quad), quad.labels
        (4, ('FL', 'FR', 'RL', 'RR'))
        """
        return cls(positions, units=units, speed_of_sound=speed_of_sound,
                   name=name)

    @classmethod
    def grid(cls, cols: int, rows: int, *,
             col_spacing: float, row_spacing: float,
             units: str = 'ft',
             speed_of_sound: Optional[float] = None,
             origin: Point = (0.0, 0.0),
             numbering: str = 'column-major',
             first_label: int = 1,
             labels: Optional[Sequence[Label]] = None,
             name: Optional[str] = None) -> 'SpeakerArray':
        """Build a rectangular grid of speakers.

        Columns run along **x** (west to east); rows run along **y** (south
        to north).  Cell ``(0, 0)`` sits at *origin*, so with the default
        origin the south-west speaker is at ``(0.0, 0.0)``.

        The numbering convention is an explicit argument because getting it
        wrong is silent and expensive.  With ``numbering='column-major'`` and
        ``first_label=1`` -- the Sonic Pavilion convention -- the label of
        the speaker in column ``c`` (0-based, west to east) and row ``r``
        (0-based, south to north) is::

            label = c * rows + r + 1

        so on a 6x4 grid speaker 1 is the south-west corner, speakers 1-4 are
        the west column running south to north, speakers 5-8 are the next
        column east, and speakers 21-24 are the east column.
        ``'row-major'`` instead numbers along each row before stepping north
        (``label = r * cols + c + 1``); the two serpentine variants reverse
        every other column or row, for a rig cabled as a snake.

        Parameters
        ----------
        cols, rows : int
            Grid size; both must be at least 1.
        col_spacing, row_spacing : float
            Centre-to-centre spacing along x and y, in *units*.  Both must be
            positive; to mirror the grid, change *origin* or *numbering*.
        units, speed_of_sound, name
            As for :class:`SpeakerArray`.
        origin : sequence of float, optional
            Position of cell ``(0, 0)``.  Two coordinates for a flat rig,
            three to give the whole plane a height.
        numbering : str, optional
            One of :data:`NUMBERINGS` (default ``'column-major'``).
        first_label : int, optional
            The label of the first speaker (default ``1``).  Pass ``0`` for
            a rig labelled from zero.
        labels : sequence, optional
            Explicit labels in numbering order, for a grid whose speakers
            carry names rather than numbers.  Mutually exclusive with
            *first_label*.

        Returns
        -------
        SpeakerArray

        Raises
        ------
        ValueError
            For a non-positive size or spacing, an unknown *numbering*, an
            origin of the wrong length, or a *labels* sequence whose length
            is not ``cols * rows``.

        Examples
        --------
        >>> pav = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
        ...                         row_spacing=60.0, name='PAVILION')
        >>> pav.position(1), pav.position(4), pav.position(21)
        ((0.0, 0.0), (0.0, 180.0), (250.0, 0.0))
        """
        if not isinstance(cols, int) or isinstance(cols, bool) \
                or not isinstance(rows, int) or isinstance(rows, bool):
            raise TypeError(
                f"cols and rows must be ints, got {cols!r} and {rows!r}.")
        if cols < 1 or rows < 1:
            raise ValueError(
                f"a grid needs at least one column and one row, got "
                f"cols={cols}, rows={rows}. For a single line of speakers "
                "use rows=1 (or cols=1).")
        cs = _as_float(col_spacing, 'col_spacing')
        rs = _as_float(row_spacing, 'row_spacing')
        if cs <= 0.0 or rs <= 0.0:
            raise ValueError(
                f"col_spacing={col_spacing!r} and row_spacing={row_spacing!r} "
                "must both be positive -- speakers at zero spacing sit on top "
                "of each other, and a negative spacing is a mirrored grid. To "
                "mirror, change origin= or numbering=.")
        org = _coerce_point(origin, 'origin')
        if len(org) not in (2, 3):
            raise ValueError(
                f"origin has {len(org)} coordinates; a grid is a plane, so "
                "its origin is (x, y) or (x, y, z).")

        cells = _grid_cells(cols, rows, numbering)

        if labels is not None:
            if first_label != 1:
                raise ValueError(
                    "pass labels= or first_label=, not both: first_label only "
                    "means anything for the generated integer labels.")
            names = list(labels)
            if len(names) != cols * rows:
                raise ValueError(
                    f"labels has {len(names)} entries but a {cols}x{rows} grid "
                    f"has {cols * rows} speakers. Give one label per speaker, "
                    f"in {numbering!r} order.")
        else:
            if not isinstance(first_label, int) or isinstance(first_label, bool):
                raise TypeError(
                    f"first_label must be an int, got {first_label!r}.")
            names = [first_label + i for i in range(len(cells))]

        pairs = []
        for label, (c, r) in zip(names, cells):
            point = (org[0] + c * cs, org[1] + r * rs)
            if len(org) == 3:
                point = point + (org[2],)
            pairs.append((label, point))
        return cls(pairs, units=units, speed_of_sound=speed_of_sound,
                   name=name, _grid_shape=(cols, rows), _numbering=numbering)

    # ------------------------------------------------------------------
    # value semantics
    # ------------------------------------------------------------------

    def __setattr__(self, key, value):
        raise AttributeError(
            f"SpeakerArray is immutable; cannot set {key!r}. Build a new "
            "array with grid() or from_positions() -- a rig that changed "
            "shape under a lowered score would silently re-route it.")

    def __delattr__(self, key):
        raise AttributeError(
            f"SpeakerArray is immutable; cannot delete {key!r}.")

    def _key(self):
        return (self._labels, self._positions, self._units, self._speed,
                self._name, self._grid_shape, self._numbering)

    def __eq__(self, other):
        if not isinstance(other, SpeakerArray):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __len__(self):
        return len(self._labels)

    def __iter__(self):
        """Iterate the speaker **labels**, in lane order."""
        return iter(self._labels)

    def __contains__(self, label):
        return label in self._lane

    def __getitem__(self, label: Label):
        """The position of *label*.  A label, never a lane index."""
        return self.position(label)

    def items(self):
        """Iterate ``(label, position)`` pairs in lane order."""
        return zip(self._labels, self._positions)

    def __repr__(self):
        name = '' if self._name is None else f"name='{self._name}', "
        shape = ''
        if self._grid_shape is not None:
            shape = (f", grid={self._grid_shape[0]}x{self._grid_shape[1]} "
                     f"{self._numbering}")
        return (f"SpeakerArray({name}speakers={len(self._labels)}, "
                f"labels=[{_format_labels(self._labels, 6)}]{shape}, "
                f"units='{self._units}', speed_of_sound={self._speed})")

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------

    @property
    def labels(self) -> tuple:
        """tuple : Speaker labels in lane order."""
        return self._labels

    @property
    def positions(self) -> tuple:
        """tuple of tuple : Speaker positions in lane order."""
        return self._positions

    @property
    def units(self) -> str:
        """str : The unit positions are measured in."""
        return self._units

    @property
    def speed_of_sound(self) -> float:
        """float : Propagation speed, in :attr:`units` per second."""
        return self._speed

    @property
    def name(self) -> Optional[str]:
        """str or None : The array's name, used in messages and ``repr``."""
        return self._name

    @property
    def grid_shape(self) -> Optional[tuple]:
        """tuple or None : ``(cols, rows)`` if built by :meth:`grid`."""
        return self._grid_shape

    @property
    def numbering(self) -> Optional[str]:
        """str or None : The label convention, if built by :meth:`grid`."""
        return self._numbering

    @property
    def dimension(self) -> int:
        """int : How many coordinates each position carries (1, 2 or 3)."""
        return len(self._positions[0])

    @property
    def centroid(self) -> tuple:
        """tuple : The mean of every speaker position -- the default listener.

        For a uniform rectangular grid this is also the geometric centre of
        the footprint (a 6x4 grid at 50 x 60 ft gives ``(125.0, 90.0)``).
        For an irregular array the two differ, and the centroid is the one
        reported here, because it is defined for every array.
        """
        n = float(len(self._positions))
        return tuple(sum(p[i] for p in self._positions) / n
                     for i in range(self.dimension))

    @property
    def centre(self) -> tuple:
        """tuple : Alias of :attr:`centroid`."""
        return self.centroid

    # ------------------------------------------------------------------
    # lookup
    # ------------------------------------------------------------------

    def _what(self) -> str:
        return "this array" if self._name is None else f"array '{self._name}'"

    def lane(self, label: Label) -> int:
        """The 0-based bus lane of *label*.

        The one place the label-to-index map is exposed, for the lowering
        that has to write ``out = srcBus + lane``.  Composers address
        speakers by label; this is engine plumbing.

        Parameters
        ----------
        label : int or str
            A speaker label declared in this array.

        Returns
        -------
        int

        Raises
        ------
        ValueError
            If no speaker carries that label.  The message lists the labels
            that do exist.
        """
        try:
            return self._lane[label]
        except (KeyError, TypeError):
            raise ValueError(
                f"no speaker labelled {label!r} in {self._what()}. Known "
                f"speakers: {_format_labels(self._labels)}. (Speakers are "
                "addressed by the label you declared, not by a 0-based "
                "index.)") from None

    def label_at(self, lane: int) -> Label:
        """The label of the speaker on 0-based bus *lane* -- the inverse of
        :meth:`lane`.

        Raises
        ------
        IndexError
            If *lane* is outside ``0..len(self) - 1``.  Negative lanes are
            refused rather than wrapped: a negative bus index is a bug, not
            a request for the last speaker.
        """
        if not isinstance(lane, int) or isinstance(lane, bool):
            raise TypeError(f"lane must be an int, got {lane!r}.")
        if not 0 <= lane < len(self._labels):
            raise IndexError(
                f"lane {lane} is outside 0..{len(self._labels) - 1} in "
                f"{self._what()}. Lanes are 0-based bus offsets; speaker "
                f"labels are {_format_labels(self._labels)}.")
        return self._labels[lane]

    def position(self, label: Label) -> tuple:
        """The position of speaker *label*.

        Raises
        ------
        ValueError
            If no speaker carries that label.
        """
        return self._positions[self.lane(label)]

    def _as_point(self, value, what: str) -> tuple:
        """Resolve a label or a raw point to a position in this array."""
        if value is None:
            return self.centroid
        if _is_label(value):
            return self.position(value)
        point = _coerce_point(value, what)
        if len(point) != self.dimension:
            raise ValueError(
                f"{what} has {len(point)} coordinates but {self._what()} is "
                f"{self.dimension}-D. Give the point the same number of "
                f"coordinates as the speakers: {self._positions[0]!r} is "
                f"speaker {self._labels[0]!r}.")
        return point

    # ------------------------------------------------------------------
    # geometry
    # ------------------------------------------------------------------

    def distance(self, a, b) -> float:
        """Distance between two speakers, or between a speaker and a point.

        Parameters
        ----------
        a, b : int, str, or sequence of float
            A speaker label, or a raw position with as many coordinates as
            the array has dimensions.  ``None`` means the array's centroid.

        Returns
        -------
        float
            Euclidean distance, in :attr:`units`.
        """
        return math.dist(self._as_point(a, 'a'), self._as_point(b, 'b'))

    def delay(self, a, b) -> float:
        """Propagation delay between two points, in seconds.

        :meth:`distance` divided by :attr:`speed_of_sound`.
        """
        return self.distance(a, b) / self._speed

    def distances(self, listener=None) -> tuple:
        """Distance from every speaker to *listener*, in lane order.

        Parameters
        ----------
        listener : label, sequence of float, or None
            Defaults to the array's :attr:`centroid`.

        Returns
        -------
        tuple of float
        """
        point = self._as_point(listener, 'listener')
        return tuple(math.dist(p, point) for p in self._positions)

    def delays(self, listener=None) -> tuple:
        """Propagation delay from every speaker to *listener*, in seconds."""
        return tuple(d / self._speed for d in self.distances(listener))

    # ------------------------------------------------------------------
    # the binaural model -- shared with the live decoder and the offline fold
    # ------------------------------------------------------------------

    def binaural_coefficients(self, listener=None, *,
                              facing: str = 'north',
                              head_half: Optional[float] = None,
                              sample_rate: Optional[int] = None,
                              max_delay: Optional[float] = None
                              ) -> BinauralCoefficients:
        """Per-speaker delay, gain and head-shadow cutoff for two ears.

        **Binaural-lite**, and deliberately not an HRTF renderer: an
        interaural time difference from the path lengths to two ear points,
        an interaural level difference from inverse distance, and a one-pole
        lowpass on whichever ear the head shadows.  It does the left-right
        axis convincingly and does not attempt front/back, which needs pinna
        filtering.  A source directly in front and one directly behind
        produce identical coefficients; that is a property of the model, not
        a defect in the array.

        The ears sit at ``listener +/- head_half`` along one axis: **x**
        when *facing* is ``'north'``, **y** when it is ``'east'``.  Facing
        east turns the listener 90 degrees, which is what rescues a gesture
        that moves only along the axis the other facing collapses.

        The same numbers drive the real-time SuperCollider decoder and the
        offline fold, which is the point of computing them here: the two
        agree on gain, delay and cutoff by construction.  They are not
        sample-identical end to end -- a one-pole in SuperCollider is not
        bit-for-bit this cutoff in a host filter, and the live path has the
        insert chain in front of it -- but nothing about the geometry can
        drift between them.

        Parameters
        ----------
        listener : label, sequence of float, or None
            Where the head is.  Defaults to the array's :attr:`centroid`.
        facing : str, optional
            ``'north'`` (default) or ``'east'``; see :data:`FACINGS`.
        head_half : float, optional
            Half the interaural distance, **in the array's units**.  Defaults
            to :data:`HEAD_HALF` for those units (0.29 ft / 0.0884 m).  An
            array in an exotic unit must pass this explicitly -- a head is
            0.29 *feet*, and reusing that number in metres would model a
            listener two feet wide.
        sample_rate : int, optional
            If given, delays come back as integer sample offsets
            (``int(round(seconds * sample_rate))``) instead of seconds --
            what an offline fold indexes with directly.
        max_delay : float, optional
            Refuse if any ear delay exceeds this many seconds.  Pass
            :data:`DECODER_MAX_DELAY_S` for the live decoder's delay line;
            the offline fold has no limit and passes nothing.

        Returns
        -------
        BinauralCoefficients

        Raises
        ------
        ValueError
            For an unknown *facing*, a non-positive *head_half*, a listener
            standing exactly on a speaker (the inverse-distance gain is
            undefined there), or a delay past *max_delay*.
        """
        if facing not in FACINGS:
            raise ValueError(
                f"facing={facing!r} is not a listener orientation; use one of "
                f"{', '.join(repr(f) for f in FACINGS)}. 'north' puts the x "
                "axis on left/right, 'east' turns the listener 90 degrees so "
                "the y axis is.")
        if head_half is None:
            if self._units not in HEAD_HALF:
                raise ValueError(
                    f"units={self._units!r} has no default head size. Pass "
                    f"head_half= (half the interaural distance, in "
                    f"{self._units}); it is {HEAD_HALF['ft']} ft / "
                    f"{HEAD_HALF['m']} m.")
            half = HEAD_HALF[self._units]
        else:
            half = _as_float(head_half, 'head_half')
            if half <= 0.0:
                raise ValueError(
                    f"head_half={head_half!r} must be positive: it is half "
                    "the distance between the ears, and at zero the two ears "
                    "are one point and there is no binaural image at all "
                    f"(it is {HEAD_HALF['ft']} ft / {HEAD_HALF['m']} m).")

        point = self._as_point(listener, 'listener')
        axis = 0 if facing == 'north' else 1
        if axis >= self.dimension:
            raise ValueError(
                f"facing='east' needs a y axis, but {self._what()} is "
                f"{self.dimension}-D. A 1-D array only has the x axis, so "
                "the listener can only face north.")
        # Facing east, north is on the listener's LEFT, so the left ear sits
        # at +y and the right at -y -- the sign is opposite the north case.
        offset = half if facing == 'north' else -half
        left = list(point)
        right = list(point)
        left[axis] = point[axis] - offset
        right[axis] = point[axis] + offset
        ear_l, ear_r = tuple(left), tuple(right)

        dl, dr, gl, gr, sl, sr = [], [], [], [], [], []
        worst_s, worst_label = 0.0, self._labels[0]
        for label, p in zip(self._labels, self._positions):
            d_l = math.dist(p, ear_l)
            d_r = math.dist(p, ear_r)
            if d_l <= 0.0 or d_r <= 0.0:
                raise ValueError(
                    f"an ear of the listener at {tuple(point)!r} lands exactly "
                    f"on speaker {label!r} at {p!r} in {self._what()}: the "
                    "inverse-distance gain is undefined at zero distance. Move "
                    f"the listener more than head_half ({half} {self._units}) "
                    "from every speaker, or audition from the array's centre "
                    "(listener=None).")
            ref = min(d_l, d_r)
            gl.append(ref / d_l)
            gr.append(ref / d_r)
            t_l = d_l / self._speed
            t_r = d_r / self._speed
            if max(t_l, t_r) > worst_s:
                worst_s, worst_label = max(t_l, t_r), label
            if sample_rate is None:
                dl.append(t_l)
                dr.append(t_r)
            else:
                dl.append(int(round(t_l * sample_rate)))
                dr.append(int(round(t_r * sample_rate)))
            # The shadow rises with how much further the far ear is,
            # saturating at one full head width -- a source straight to one
            # side, where the extra path is exactly 2 * head_half.
            a_l = min(1.0, max(0.0, (d_l - d_r) / (2.0 * half)))
            a_r = min(1.0, max(0.0, (d_r - d_l) / (2.0 * half)))
            sl.append(SHADOW_HI_HZ + (SHADOW_LO_HZ - SHADOW_HI_HZ) * a_l)
            sr.append(SHADOW_HI_HZ + (SHADOW_LO_HZ - SHADOW_HI_HZ) * a_r)

        if max_delay is not None:
            limit = _as_float(max_delay, 'max_delay')
            if worst_s > limit:
                raise ValueError(
                    f"the furthest speaker in {self._what()} ({worst_label!r}) "
                    f"is {worst_s:.2f} s from the listener at "
                    f"{tuple(point)!r}, past the {limit:.2f} s delay line. "
                    "Move the listener inside the array, or fold this one "
                    "offline, which has no delay limit.")

        return BinauralCoefficients(
            labels=self._labels,
            delay_l=tuple(dl), delay_r=tuple(dr),
            gain_l=tuple(gl), gain_r=tuple(gr),
            shadow_l_hz=tuple(sl), shadow_r_hz=tuple(sr),
            listener=tuple(point), facing=facing, head_half=half,
            sample_rate=None if sample_rate is None else int(sample_rate))

    # ------------------------------------------------------------------
    # orderings a composer reaches for
    # ------------------------------------------------------------------

    def serpentine(self, axis: str = 'column', start: str = 'sw',
                   reverse: bool = False) -> tuple:
        """A boustrophedon path over the grid -- every speaker once, no jumps.

        The snake a sweep is usually written against: it runs a column south
        to north, steps east, runs back north to south, and so on, so
        consecutive steps are always adjacent.  Derived from the grid, not
        from any venue's list, so it follows *this* array's shape and
        numbering.

        Parameters
        ----------
        axis : str, optional
            ``'column'`` (default) runs each pass along a column and steps
            sideways between passes; ``'row'`` runs each pass along a row.
        start : str, optional
            The corner to start from: one of :data:`START_CORNERS`
            (``'sw'``, ``'nw'``, ``'se'``, ``'ne'``).
        reverse : bool, optional
            Reverse the whole path.

        Returns
        -------
        tuple
            Speaker labels, one per speaker.

        Raises
        ------
        ValueError
            If this array has no grid (built by :meth:`from_positions`), or
            for an unknown *axis* or *start*.

        Examples
        --------
        >>> pav = SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0,
        ...                         row_spacing=60.0)
        >>> pav.serpentine()[:8]
        (1, 2, 3, 4, 8, 7, 6, 5)
        """
        if self._grid_shape is None:
            raise ValueError(
                f"serpentine() needs a grid, and {self._what()} was built "
                "from explicit positions, so it has no columns or rows. Build "
                "it with SpeakerArray.grid(...), or sweep it with "
                "axis_order('x'), which works on any array.")
        if axis not in ('column', 'row'):
            raise ValueError(
                f"axis={axis!r} must be 'column' (each pass runs up a column) "
                "or 'row' (each pass runs along a row).")
        if start not in START_CORNERS:
            raise ValueError(
                f"start={start!r} must be one of "
                f"{', '.join(repr(s) for s in START_CORNERS)} -- the corner "
                "the snake begins at, west/east then south/north.")

        cols, rows = self._grid_shape
        cell_lane = {cell: i for i, cell in
                     enumerate(_grid_cells(cols, rows, self._numbering))}
        # start is 'sw'/'nw'/'se'/'ne': first letter is the south/north half,
        # second is the west/east half.
        south = start[0] == 's'
        west = start[1] == 'w'
        col_seq = list(range(cols)) if west else list(range(cols - 1, -1, -1))
        row_seq = list(range(rows)) if south else list(range(rows - 1, -1, -1))

        out = []
        if axis == 'column':
            for i, c in enumerate(col_seq):
                seq = row_seq if i % 2 == 0 else row_seq[::-1]
                out.extend(self._labels[cell_lane[(c, r)]] for r in seq)
        else:
            for i, r in enumerate(row_seq):
                seq = col_seq if i % 2 == 0 else col_seq[::-1]
                out.extend(self._labels[cell_lane[(c, r)]] for c in seq)
        return tuple(reversed(out)) if reverse else tuple(out)

    def axis_order(self, axis: Union[str, int] = 'x',
                   reverse: bool = False) -> tuple:
        """Speaker labels sorted along one axis -- a straight sweep.

        Works on any array, grid or not.  Ties break on the remaining
        coordinates and then on lane, so the order is total and the same
        every run.

        Parameters
        ----------
        axis : str or int, optional
            ``'x'``, ``'y'``, ``'z'`` or a 0-based coordinate index.
        reverse : bool, optional
            Sweep the other way (east to west, north to south).

        Returns
        -------
        tuple
            Speaker labels.

        Raises
        ------
        ValueError
            For an unknown axis name, or an axis this array does not have.
        """
        names = ('x', 'y', 'z')
        if isinstance(axis, str):
            if axis not in names:
                raise ValueError(
                    f"axis={axis!r} must be 'x', 'y', 'z' or a 0-based index.")
            index = names.index(axis)
        elif isinstance(axis, int) and not isinstance(axis, bool):
            index = axis
        else:
            raise TypeError(f"axis must be 'x', 'y', 'z' or an int, got {axis!r}.")
        if not 0 <= index < self.dimension:
            raise ValueError(
                f"axis {axis!r} is index {index}, but {self._what()} is "
                f"{self.dimension}-D, so its axes are "
                f"{', '.join(names[:self.dimension])}.")
        order = sorted(
            range(len(self._labels)),
            key=lambda i: (self._positions[i][index],
                           self._positions[i], i))
        if reverse:
            order.reverse()
        return tuple(self._labels[i] for i in order)
