# OpenMusic spacing port

Horizontal spacing follows **OpenMusic** `space-packet` / `space-size&offset` / `ryhtm2pixels` from:

`OPENMUSIC/code/projects/musicproject/editor/scoreeditor/scoretools.lisp` (see also `scoreeditors.lisp` for `timebpf`, `get-x-pos`).

Local Lisp trees may live under `~/Downloads/openmusic-master 2/` or similar; paths in `NEXT_STEPS.md` are authoritative.

## Python modules

- `spacing/om_packet.py` — `ryhtm2pixels`, `space_packet`, `space_size_offset_measure`, `layout_single_measure_events_om`, `space_with_barlines_om`, `build_timebpf_with_sentinel`, `interp_timebpf`.

## Integration

- `pipeline.notate`: `spacing_mode` `hybrid` or `om` → OM packet layout for barlined measures (`layout_single_measure_events_om` / `space_with_barlines_om`). Other modes keep legacy `space_proportional` / `space_traditional` / `space_with_barlines`.

- `pipeline_bt.notate_bt`: global time-ordered OM packet walk across staves (`_apply_om_packet_layout_bt`); post-layout BPF from event anchors + OM-style sentinel; barlines via `interp_timebpf`.

## Klotho-only (not from OM)

- `TemporalBlock.axis` and row `offset` alignment in seconds (`klotho/chronos/temporal_units/temporal.py`).
- `render_score` / `_render_row` `row_start_x` and system bracket policy for non-left-aligned blocks.
- SMuFL glyph widths: `compute_min_space` / renderer constants stand in for OM grap `rectangle` / `delta-head`.
