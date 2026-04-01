"""UTS pipeline: TemporalUnitSequence → NotatedSystem → SVG.

Converts a TemporalUnitSequence (flat list of TemporalUnit/CompositionalUnit
or nested sub-UTSs) into a horizontal system of NotatedMeasures.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from klotho.chronos import TemporalUnit, TemporalUnitSequence

from .models import NotatedMeasure, NotatedSystem
from .pipeline import notate


def notate_uts(
    uts,
    spacing_mode: str = 'hybrid',
    max_dots: int = 2,
    scale: float = 400.0,
    left_margin: float = 62.0,
    barlines: bool = True,
) -> NotatedSystem:
    """Convert a TemporalUnitSequence into a horizontal system of NotatedMeasures.

    Handles:
    - Flat lists of TemporalUnit / CompositionalUnit
    - Nested sub-TemporalUnitSequences (each ends with a double barline)

    Does NOT yet handle TemporalBlocks as sequence elements.

    Parameters
    ----------
    uts : TemporalUnitSequence
        The sequence to notate.
    spacing_mode : str
        One of 'proportional', 'traditional', 'hybrid'.
    barlines : bool
        When True, draw barlines and time signatures per unit.
    """
    measures: list[NotatedMeasure] = []
    prev_meas = None
    new_group = True

    for unit in uts.seq:
        if isinstance(unit, TemporalUnitSequence):
            sub_system = notate_uts(
                unit,
                spacing_mode=spacing_mode,
                max_dots=max_dots,
                scale=scale,
                left_margin=left_margin,
                barlines=barlines,
            )
            measures.extend(sub_system.measures)
            if measures:
                measures[-1].end_barline_type = 'double'
            if sub_system.measures:
                lm = sub_system.measures[-1].time_signature
                prev_meas = lm
            new_group = True
        else:
            if not barlines:
                show_ts = True
                metric_changed = False
                fg = True
                fmv = True
            else:
                show_ts = should_show_time_sig(unit.rt.meas, prev_meas)
                metric_changed = (
                    prev_meas is not None
                    and (
                        unit.rt.meas.numerator != prev_meas.numerator
                        or unit.rt.meas.denominator != prev_meas.denominator
                    )
                )
                fg = new_group
                fmv = new_group

            m = notate(
                unit.rt,
                spacing_mode=spacing_mode,
                max_dots=max_dots,
                scale=scale,
                left_margin=left_margin,
                barlines=barlines,
                tempo_beat=unit.beat,
                tempo_bpm=unit.bpm,
                om_first_of_group=fg,
                om_first_measure_of_voice=fmv,
                om_show_time_sig=show_ts,
                om_metric_changed=metric_changed,
            )
            measures.append(m)
            prev_meas = unit.rt.meas
            new_group = False

    return NotatedSystem(measures=measures)


def should_show_tempo(
    current_beat: Optional[Fraction],
    current_bpm: Optional[float],
    prev_beat: Optional[Fraction],
    prev_bpm: Optional[float],
) -> bool:
    """Determine whether to show tempo at this position (changed from previous)."""
    if prev_beat is None and prev_bpm is None:
        return True  # First unit always shows tempo
    return current_beat != prev_beat or current_bpm != prev_bpm


def should_show_time_sig(current_meas, prev_meas) -> bool:
    """Determine whether to show time signature (changed from previous)."""
    if prev_meas is None:
        return True  # First unit always shows time sig
    return (current_meas.numerator != prev_meas.numerator or
            current_meas.denominator != prev_meas.denominator)
