# -*- coding: utf-8 -*-
"""Width check for the guide/journal panel, which is narrower than a text box.

Same idea as check_line_width.py but with the guide's own budget: the widest
line the English Guide.txt ever used. Section labels get their own, tighter
budget -- they are drawn into the left-hand menu's tile allocation, and going
over it is what left black smudges over the lower entries.

Run from repo root:
    python TMGC_Buildfiles/KoreanPatch/check_guide_width.py
"""
import io
import json
import os
import re
import struct
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = 'TMGC_Buildfiles/Text/Guide.txt'
CLEAN = os.path.join(ROOT, 'TMGC_Buildfiles', 'FE8_clean.gba')
BASELINE = '709b897'
DIALOG_FONT = 0x58F6F4
KR_ADVANCE = 12
BREAK = re.compile(r'\[(?:N|NL|2NL)\]')


def ascii_widths():
    rom = open(CLEAN, 'rb').read()
    w = {}
    for c in range(256):
        ptr = struct.unpack_from('<I', rom, DIALOG_FONT + c * 4)[0]
        if 0x08000000 <= ptr < 0x08000000 + len(rom):
            w[c] = rom[(ptr - 0x08000000) + 5]
    return w


AW = ascii_widths()
DEF = AW.get(0x3F, 8)


def width_of(text):
    s = re.sub(r'\[[^\]\n]*\]', '', text)
    return sum(AW.get(ord(c), DEF) if ord(c) < 0x80 else KR_ADVANCE for c in s)


def widest(line):
    return max((width_of(s) for s in BREAK.split(line)), default=0)


def body_lines(txt):
    return [l for l in txt.splitlines()
            if l and not l.startswith('#') and not l.lstrip().startswith('//')]


def sections(txt):
    return dict(re.findall(r'##\s*(GuideSection\d)\s*\n([^\n]+)', txt))


def main():
    r = subprocess.run(['git', 'show', '%s:%s' % (BASELINE, GUIDE)],
                       cwd=ROOT, capture_output=True)
    orig = r.stdout.decode('utf-8', 'replace')
    cur = io.open(os.path.join(ROOT, GUIDE), encoding='utf-8').read()

    budget = max(widest(l) for l in body_lines(orig))
    sec_budget = max(width_of(v) for v in sections(orig).values())
    print('body budget    : %d px  (widest English guide line)' % budget)
    print('section budget : %d px  (widest English section label)' % sec_budget)

    bad_sec = [(k, v.strip(), width_of(v)) for k, v in sections(cur).items()
               if width_of(v) > sec_budget]
    print('\nsection labels over budget: %d' % len(bad_sec))
    for k, v, w in bad_sec:
        print('  %-16s %-14s %dpx' % (k, v, w))

    over = []
    for i, l in enumerate(io.open(os.path.join(ROOT, GUIDE), encoding='utf-8'), 1):
        l = l.rstrip('\n')
        if l.startswith('#') or l.lstrip().startswith('//'):
            continue
        w = widest(l)
        if w > budget:
            over.append({'line': i, 'width': w, 'text': l.strip()})
    print('\nbody lines over budget: %d' % len(over))
    for x in over[:40]:
        print('  %4d  %3dpx  %s' % (x['line'], x['width'], x['text'][:56]))

    json.dump({'budget': budget, 'section_budget': sec_budget, 'lines': over},
              io.open(os.path.join(HERE, '_guide_over.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\nreport -> KoreanPatch/_guide_over.json')


if __name__ == '__main__':
    main()
