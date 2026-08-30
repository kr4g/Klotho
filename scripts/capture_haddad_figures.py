"""Capture Haddad's published rhythm-tree figures from the thesis PDF.

THIS IS A CORRECTNESS ORACLE, and the only one this project has.

Everything else in tests/ is a REGRESSION oracle: it was captured from Klotho's
own output at some past moment, so it can prove that behaviour has not changed
and can never prove that behaviour is right. The values written here come from
outside the codebase entirely -- from the printed source Klotho claims to
implement -- so they can.

WHY THIS IS EXTRACTABLE AT ALL. For the rhythm-tree figures of chapter 2,
Haddad prints the OpenMusic s-expression as MACHINE-READABLE TEXT above the
engraving. ``pdftotext`` recovers it exactly. That is not true everywhere: the
operator figures of section 4.5 carry their meaning in glyphs, and pdftotext
destroys every one of them -- those pages must be read as images instead.

SOURCE
    Karim Haddad, "Le Temps et la Forme", doctoral thesis, 2020.
    PDF page = thesis page + 9 (verified: PDF p288 carries "279" in its header).
    The PDF is NOT in this repository -- it is a copyrighted document, and
    kr4g/Klotho is public. Point THESIS_PDF at your own copy.

USAGE
    KLOTHO_ALLOW_REGEN=1 python scripts/capture_haddad_figures.py \
        --pdf "/path/to/HADDAD_Karim_2020_Thesis.pdf" \
        > tests/fixtures/haddad_figures.json

The oracle lock guards this like every other capture path. Unlike the others it
does NOT require a remote build -- it never imports klotho at all, which is the
whole point: nothing Klotho does can influence what this writes.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tests'))
from _oracle_lock import require_regen_authorization

PAGE_OFFSET = 9

#: Thesis pages known to print s-expressions above their engravings. Chapter 2
#: only -- see the module docstring for why section 4.5 cannot be read this way.
PAGES = tuple(range(279, 296))


def sexprs_on(pdf, thesis_page):
    """Every balanced ``(? ...)`` expression on one thesis page, with its figure number."""
    p = thesis_page + PAGE_OFFSET
    txt = subprocess.run(
        ['pdftotext', '-f', str(p), '-l', str(p), '-layout', str(pdf), '-'],
        capture_output=True, text=True, check=True).stdout
    out = []
    # Two printed forms, both machine-readable:
    #   ``(? (((8 2) ...``   the chapter-2 transformation figures
    #   ``(1 (((4 4) ...``   the autoreference figures (2.17-2.20)
    # Figure 2.18 is printed WITHOUT its opening paren -- ``1 (((4 4) ...`` --
    # which is a typo in the thesis, not an extraction artifact. It is captured
    # with the paren restored and flagged, rather than silently repaired.
    for m in re.finditer(r'(?m)^\s*(\(\?|\(\d+|\d+)\s*\(\(', txt):
        start = m.start()
        repaired = False
        if not txt[start:].lstrip().startswith('('):
            # bare leading integer: the thesis dropped the opening paren
            start = start + txt[start:].index(txt[start:].lstrip()[0])
            repaired = True
        depth = 1 if repaired else 0
        for j in range(start, len(txt)):
            if txt[j] == '(':
                depth += 1
            elif txt[j] == ')':
                depth -= 1
                if depth == 0:
                    label = re.search(r'Figure (\d+\.\d+)', txt[j:j + 500])
                    raw = ' '.join(txt[start:j + 1].split())
                    out.append({
                        'figure': label.group(1) if label else None,
                        'thesis_page': thesis_page,
                        'pdf_page': p,
                        'sexpr': ('(' + raw) if repaired else raw,
                        'printed_unbalanced': repaired,
                    })
                    break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    args = ap.parse_args()

    require_regen_authorization('tests/fixtures/haddad_figures.json')

    pdf = Path(args.pdf).expanduser()
    if not pdf.is_file():
        raise SystemExit(f'thesis PDF not found: {pdf}')

    figures = {}
    for t in PAGES:
        for rec in sexprs_on(pdf, t):
            if rec['figure'] and rec['figure'] not in figures:
                figures[rec['figure']] = rec

    json.dump({
        'source': 'Karim Haddad, Le Temps et la Forme (thesis, 2020)',
        'provenance': ('pdftotext -layout, one page at a time; PDF page = thesis page + '
                       f'{PAGE_OFFSET}. Values are Haddad\'s printed OpenMusic '
                       's-expressions, not Klotho output.'),
        'extracted_by': 'scripts/capture_haddad_figures.py',
        'figures': dict(sorted(figures.items(), key=lambda kv: [int(x) for x in kv[0].split('.')])),
    }, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
