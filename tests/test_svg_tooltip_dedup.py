"""Tooltip line-table dedup (svg_shared.render_tooltip_system).

The embedded ``var data=...`` payload is a line-table reconstruction; these
tests pin the Python-side encoding against the exact join semantics the
generated JS uses, and the fallback for non-string entries.
"""
import json
import re

from klotho.semeios.visualization._shared.svg_shared import (
    _dedup_hover_texts, render_tooltip_system)


CASES = [
    [],
    [""],
    ["single"],
    ["a\nb", "a\nc", "a\nb"],
    ["header\n\nbody", "header\n\nbody\n", "\nleading", "trailing\n"],
    ["unicode: ¢éñ\nsame line", "unicode: ¢éñ\nother"],
    ['quotes "x" and \\backslash\\\nshared', 'quotes "x" and \\backslash\\\nshared'],
]


def _reconstruct(lines, encoded):
    # exact mirror of the generated JS: a.map(i => L[i]).join("\n")
    return ['\n'.join(lines[i] for i in idxs) for idxs in encoded]


def test_dedup_round_trips_exactly():
    for texts in CASES:
        lines, encoded = _dedup_hover_texts(texts)
        assert _reconstruct(lines, encoded) == texts
        assert len(lines) == len(set(lines))


def test_dedup_shrinks_repetitive_corpus():
    texts = [f"Item: drums [drums]\nUnit {i % 4}\nleaf {i % 7}\ndur: 0.25s"
             for i in range(200)]
    lines, encoded = _dedup_hover_texts(texts)
    deduped = len(json.dumps(lines)) + len(json.dumps(encoded))
    assert deduped < len(json.dumps(texts)) * 0.5


def test_render_embeds_line_table_for_strings():
    html = render_tooltip_system("uidx", ["a\nb", "a\nc"])
    assert 'var data=(function(){var L=' in html
    assert '"a"' in html and '"b"' in html and '"c"' in html


def test_script_close_tag_cannot_break_out():
    # '</script>' inside a tooltip must not terminate the <script> element:
    # the embedded JSON escapes '</' as '<\/'.
    html = render_tooltip_system("uidx", ["</scr" + "ipt> boom\nshared"])
    payload = html.split('var data=', 1)[1]
    assert '</scr' + 'ipt>' not in payload.split(';\n', 1)[0]
    assert '<\\/scr' + 'ipt>' in payload


def test_render_falls_back_for_non_strings():
    html = render_tooltip_system("uidx", [None, "text"])
    m = re.search(r'var data=(\[.*?\]);', html)
    assert m is not None
    assert json.loads(m.group(1)) == [None, "text"]
