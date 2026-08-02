# -*- coding: utf-8 -*-
"""Measure the rendered pixel width of every dialogue line and flag overflow.

FE8 draws each [N]-delimited line into a fixed-width buffer. A line wider than
that buffer does not wrap -- it is dropped or spills into neighbouring tiles,
which is why some Korean lines render as an empty text box or as garbled
glyphs partway through.

Budget: the original English script was authored to fit, so the widest
original line is a safe upper bound. ASCII advances come from the real FE8
dialogue font in the clean ROM; Korean advances come from gen_font.py
(uniform 12px dialogue / 11px menu).

Run from repo root:
    python TMGC_Buildfiles/KoreanPatch/check_line_width.py
"""
import io, json, os, re, struct, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = 'TMGC_Buildfiles/Text'
CLEAN = os.path.join(ROOT, 'TMGC_Buildfiles', 'FE8_clean.gba')

DIALOG_FONT = 0x58F6F4          # glyph pointer table, 256 entries
KR_ADVANCE = 12                 # gen_font.py 'dialog' uniform_advance
BASELINE = '709b897'            # last commit before any translation


def ascii_widths():
    """width for each byte 0..255 from the clean ROM's dialogue font."""
    rom = open(CLEAN, 'rb').read()
    w = {}
    for c in range(256):
        ptr = struct.unpack_from('<I', rom, DIALOG_FONT + c * 4)[0]
        if not (0x08000000 <= ptr < 0x08000000 + len(rom)):
            continue
        w[c] = rom[(ptr - 0x08000000) + 5]
    return w


AW = ascii_widths()
DEFAULT_ASCII = AW.get(0x3F, 8)


BREAK = re.compile(r'\[(?:N|NL|2NL)\]')


def segments(line):
    """Split a source line into the display lines it actually produces.

    A break code can sit mid-line -- "name/name:[N]4/8/22[N]" is two rows on
    screen, not one -- so measuring the raw line overstates its width.
    """
    return BREAK.split(line)


def width_of(text):
    """Rendered width in px of one display line (bracket codes are not drawn)."""
    s = re.sub(r'\[[^\]\n]*\]', '', text)
    total = 0
    for ch in s:
        if ord(ch) < 0x80:
            total += AW.get(ord(ch), DEFAULT_ASCII)
        else:
            total += KR_ADVANCE
    return total


def widest(line):
    return max((width_of(s) for s in segments(line)), default=0)


def git_show(rev, path):
    r = subprocess.run(['git', 'show', '%s:%s' % (rev, path)], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', 'replace')


files = json.load(io.open(os.path.join(HERE, '_translate_filelist.json'), encoding='utf-8'))

# ---- 1. budget from the original English ----
budget = 0
budget_src = ''
for rel in files:
    orig = git_show(BASELINE, TEXT + '/' + rel.replace('\\', '/'))
    if not orig:
        continue
    for ln in orig.splitlines():
        if ln.startswith('#') or ln.lstrip().startswith('//'):
            continue
        w = widest(ln)
        if w > budget:
            budget, budget_src = w, '%s: %s' % (rel, ln.strip()[:60])

print('widest original English line: %d px' % budget)
print('  %s\n' % budget_src)

# ---- 2. measure the Korean ----
over = []
for rel in files:
    p = os.path.join(ROOT, TEXT, rel)
    if not os.path.isfile(p):
        continue
    for i, ln in enumerate(io.open(p, encoding='utf-8', errors='replace'), 1):
        ln = ln.rstrip('\n')
        if ln.startswith('#') or ln.lstrip().startswith('//'):
            continue
        w = widest(ln)
        if w > budget:
            over.append({'file': rel, 'line': i, 'width': w,
                         'text': ln.strip()})

over.sort(key=lambda d: -d['width'])
print('lines wider than the budget: %d' % len(over))
per_file = {}
for d in over:
    per_file[d['file']] = per_file.get(d['file'], 0) + 1
print('files affected: %d\n' % len(per_file))

print('--- worst offenders ---')
for d in over[:25]:
    print('  %4dpx  %s:%d' % (d['width'], d['file'], d['line']))
    print('          %s' % d['text'][:64])

print('\n--- worst files ---')
for f, c in sorted(per_file.items(), key=lambda kv: -kv[1])[:15]:
    print('  %-52s %d' % (f, c))

json.dump({'budget_px': budget, 'count': len(over), 'lines': over},
          io.open(os.path.join(HERE, '_overwide_lines.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nreport -> KoreanPatch/_overwide_lines.json')
