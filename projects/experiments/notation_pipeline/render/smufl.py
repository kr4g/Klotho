"""SMuFL glyph lookup and metrics for Bravura font."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models import NoteType

# Path to Bravura assets
_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_METADATA_PATH = _ASSETS_DIR / "bravura_metadata.json"

# Lazy-loaded metadata
_metadata: Optional[dict] = None


def _load_metadata() -> dict:
    global _metadata
    if _metadata is None:
        with open(_METADATA_PATH, 'r') as f:
            _metadata = json.load(f)
    return _metadata


# SMuFL glyph name -> Unicode code point (in Bravura PUA)
GLYPH_CODEPOINTS: dict[str, str] = {
    # Noteheads
    "noteheadBlack":        "\uE0A4",   # filled (quarter and shorter)
    "noteheadHalf":         "\uE0A3",   # open (half note)
    "noteheadWhole":        "\uE0A2",   # whole note
    # Rests
    "restWhole":            "\uE4E3",
    "restHalf":             "\uE4E4",
    "restQuarter":          "\uE4E5",
    "rest8th":              "\uE4E6",
    "rest16th":             "\uE4E7",
    "rest32nd":             "\uE4E8",
    "rest64th":             "\uE4E9",
    "rest128th":            "\uE4EA",
    # Flags (up-stem)
    "flag8thUp":            "\uE240",
    "flag16thUp":           "\uE242",
    "flag32ndUp":           "\uE244",
    "flag64thUp":           "\uE246",
    "flag128thUp":          "\uE248",
    # Flags (down-stem)
    "flag8thDown":          "\uE241",
    "flag16thDown":         "\uE243",
    "flag32ndDown":         "\uE245",
    "flag64thDown":         "\uE247",
    "flag128thDown":        "\uE249",
    # Augmentation dot
    "augmentationDot":      "\uE1E7",
    # Time signature digits
    "timeSig0":             "\uE080",
    "timeSig1":             "\uE081",
    "timeSig2":             "\uE082",
    "timeSig3":             "\uE083",
    "timeSig4":             "\uE084",
    "timeSig5":             "\uE085",
    "timeSig6":             "\uE086",
    "timeSig7":             "\uE087",
    "timeSig8":             "\uE088",
    "timeSig9":             "\uE089",
    # Tuplet digits
    "tuplet0":              "\uE880",
    "tuplet1":              "\uE881",
    "tuplet2":              "\uE882",
    "tuplet3":              "\uE883",
    "tuplet4":              "\uE884",
    "tuplet5":              "\uE885",
    "tuplet6":              "\uE886",
    "tuplet7":              "\uE887",
    "tuplet8":              "\uE888",
    "tuplet9":              "\uE889",
    # Tuplet colon
    "tupletColon":          "\uE88A",
    # Barlines
    "barlineSingle":        "\uE030",
    "barlineDouble":        "\uE031",
    "barlineFinal":         "\uE032",
    # Percussion clef
    "unpitchedPercussionClef1": "\uE069",
    # Metronome marks (for tempo markings)
    "metNoteWhole":         "\uECA2",
    "metNoteHalfUp":        "\uECA3",
    "metNoteQuarterUp":     "\uECA5",
    "metNote8thUp":         "\uECA7",
    "metNote16thUp":        "\uECA9",
    "metNote32ndUp":        "\uECAB",
    "metAugmentationDot":   "\uECB7",
}


def notehead_glyph(note_type: NoteType) -> str:
    """Return the SMuFL glyph character for a notehead."""
    if note_type == NoteType.WHOLE:
        return GLYPH_CODEPOINTS["noteheadWhole"]
    elif note_type == NoteType.HALF:
        return GLYPH_CODEPOINTS["noteheadHalf"]
    else:
        return GLYPH_CODEPOINTS["noteheadBlack"]


def rest_glyph(note_type: NoteType) -> str:
    """Return the SMuFL glyph character for a rest."""
    rest_map = {
        NoteType.WHOLE:   GLYPH_CODEPOINTS["restWhole"],
        NoteType.HALF:    GLYPH_CODEPOINTS["restHalf"],
        NoteType.QUARTER: GLYPH_CODEPOINTS["restQuarter"],
        NoteType.EIGHTH:  GLYPH_CODEPOINTS["rest8th"],
        NoteType.N16TH:   GLYPH_CODEPOINTS["rest16th"],
        NoteType.N32ND:   GLYPH_CODEPOINTS["rest32nd"],
        NoteType.N64TH:   GLYPH_CODEPOINTS["rest64th"],
        NoteType.N128TH:  GLYPH_CODEPOINTS["rest128th"],
    }
    return rest_map.get(note_type, GLYPH_CODEPOINTS["restQuarter"])


def flag_glyph(note_type: NoteType, stem_up: bool = True) -> Optional[str]:
    """Return the flag glyph for a note type (only for unbeamed notes)."""
    suffix = "Up" if stem_up else "Down"
    flag_map = {
        NoteType.EIGHTH:  GLYPH_CODEPOINTS[f"flag8th{suffix}"],
        NoteType.N16TH:   GLYPH_CODEPOINTS[f"flag16th{suffix}"],
        NoteType.N32ND:   GLYPH_CODEPOINTS[f"flag32nd{suffix}"],
        NoteType.N64TH:   GLYPH_CODEPOINTS[f"flag64th{suffix}"],
        NoteType.N128TH:  GLYPH_CODEPOINTS[f"flag128th{suffix}"],
    }
    return flag_map.get(note_type)


def time_sig_glyphs(numerator: int, denominator: int) -> tuple[str, str]:
    """Return SMuFL glyph strings for a time signature's numerator and denominator."""
    def digits_to_glyphs(n: int) -> str:
        return "".join(GLYPH_CODEPOINTS[f"timeSig{d}"] for d in str(n))
    return digits_to_glyphs(numerator), digits_to_glyphs(denominator)


def tuplet_number_glyphs(n: int) -> str:
    """Return SMuFL glyph string for a tuplet number."""
    return "".join(GLYPH_CODEPOINTS[f"tuplet{d}"] for d in str(n))


def has_stem(note_type: NoteType) -> bool:
    """Whether this note type requires a stem."""
    return note_type != NoteType.WHOLE


def metronome_glyph_and_dots(beat_fraction) -> tuple[str, int]:
    """Return SMuFL metronome glyph and dot count for a beat value.

    Parameters
    ----------
    beat_fraction : Fraction
        Beat duration in whole notes (e.g., 1/4 for quarter note).

    Returns
    -------
    (str, int)
        Base metronome glyph and number of augmentation dots (0, 1, or 2).
    """
    from fractions import Fraction
    beat = Fraction(beat_fraction)

    base_map = {
        Fraction(1, 1): GLYPH_CODEPOINTS["metNoteWhole"],
        Fraction(1, 2): GLYPH_CODEPOINTS["metNoteHalfUp"],
        Fraction(1, 4): GLYPH_CODEPOINTS["metNoteQuarterUp"],
        Fraction(1, 8): GLYPH_CODEPOINTS["metNote8thUp"],
        Fraction(1, 16): GLYPH_CODEPOINTS["metNote16thUp"],
        Fraction(1, 32): GLYPH_CODEPOINTS["metNote32ndUp"],
    }

    # Undotted
    if beat in base_map:
        return base_map[beat], 0

    # Single dot (base * 3/2)
    undotted = beat * Fraction(2, 3)
    if undotted in base_map:
        return base_map[undotted], 1

    # Double dot (base * 7/4)
    undotted2 = beat * Fraction(4, 7)
    if undotted2 in base_map:
        return base_map[undotted2], 2

    # Fallback
    return base_map[Fraction(1, 4)], 0
