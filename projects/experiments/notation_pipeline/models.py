"""Data models for the notation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from fractions import Fraction
from typing import Optional


class NoteType(Enum):
    """Standard Western note durations as powers of two."""
    WHOLE = auto()       # 1/1
    HALF = auto()        # 1/2
    QUARTER = auto()     # 1/4
    EIGHTH = auto()      # 1/8
    N16TH = auto()       # 1/16
    N32ND = auto()       # 1/32
    N64TH = auto()       # 1/64
    N128TH = auto()      # 1/128


# Base duration (in whole notes) for each NoteType
NOTE_TYPE_DURATIONS: dict[NoteType, Fraction] = {
    NoteType.WHOLE:   Fraction(1, 1),
    NoteType.HALF:    Fraction(1, 2),
    NoteType.QUARTER: Fraction(1, 4),
    NoteType.EIGHTH:  Fraction(1, 8),
    NoteType.N16TH:   Fraction(1, 16),
    NoteType.N32ND:   Fraction(1, 32),
    NoteType.N64TH:   Fraction(1, 64),
    NoteType.N128TH:  Fraction(1, 128),
}


@dataclass(frozen=True)
class EngravingLeaf:
    """A single engravable note or rest after tie-splitting."""
    node_id: int                    # Back-reference to the RT node
    duration: Fraction              # Engravable duration (positive, in whole notes)
    onset: Fraction                 # Metric onset within the measure
    note_type: NoteType             # Classified note type
    dots: int = 0                   # 0, 1, or 2
    is_rest: bool = False
    is_continuation_tie: bool = False   # True if this is a tied continuation (not a new attack)
    is_tied_forward: bool = False       # True if tied to the next event
    tuplet_scale: Optional[Fraction] = None  # Tuplet scaling factor if inside a tuplet
    # Spacing (filled in by spacing pass)
    x: float = 0.0


@dataclass
class TupletBracket:
    """An N:M tuplet bracket."""
    actual: int                     # e.g. 3 in "3:2"
    normal: int                     # e.g. 2 in "3:2"
    inner_note_type: Optional[NoteType]  # Note type inside the bracket
    event_indices: list[int] = field(default_factory=list)  # Indices into events list
    group_node_id: int = -1         # RT node that generated this tuplet


@dataclass
class BeamGroup:
    """A group of beamed notes."""
    event_indices: list[int] = field(default_factory=list)
    max_beam_level: int = 0
    group_node_id: int = -1


@dataclass
class NotatedMeasure:
    """Complete notation data for one or more measures (when span > 1)."""
    time_signature: object          # Meas object (kept generic to avoid import)
    events: list[EngravingLeaf] = field(default_factory=list)
    tuplets: list[TupletBracket] = field(default_factory=list)
    beam_groups: list[BeamGroup] = field(default_factory=list)
    rt_text: str = ""               # String representation of the RT for comparison
    barline_x_positions: list = field(default_factory=list)  # All barline x positions (start, internal, end)
    show_barlines: bool = True      # Whether to draw barlines and time signature
    tempo_beat: Optional[Fraction] = None  # Beat unit for tempo marking (e.g., 1/4)
    tempo_bpm: Optional[float] = None      # BPM for tempo marking
    end_barline_type: str = 'single'       # 'single', 'double', 'final', 'none'


@dataclass
class NotatedSystem:
    """A horizontal system of measures (for TemporalUnitSequence rendering)."""
    measures: list[NotatedMeasure] = field(default_factory=list)


@dataclass
class NotatedScore:
    """A multi-staff score (for TemporalBlock rendering).

    Each row is a NotatedSystem representing one staff/voice.
    Rows are stacked vertically with a system bracket on the left.
    """
    rows: list[NotatedSystem] = field(default_factory=list)
