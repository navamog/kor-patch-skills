# -*- coding: utf-8 -*-
"""Re-check line widths with the *narrow* font measured correctly.

check_line_width.py reads ASCII advances from the clean ROM. That is right for
ordinary entries but wrong for entries marked `^`, which render through the
narrow font installed by the hack -- those glyph slots (0x81..0xBC) are empty in
the clean ROM, so the checker fell back to 8px per character when the real
advance is 4-5px. Every `^` budget derived that way was inflated by roughly 2x,
and Korean lines that overflow on screen passed the check.

This measures the narrow glyphs from the *built* ROM and re-derives each file's
budget from the widest English display line in the pre-translation baseline.

Run from repo root:
    python TMGC_Buildfiles/KoreanPatch/check_narrow_width.py
"""
import io
import json
import os
import re
import struct
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEXT = 'TMGC_Buildfiles/Text'
BUILT = os.path.join(ROOT, 'TMGC_Buildfiles', 'TMGC2.gba')
DIALOG_FONT = 0x58F6F4
KR_ADVANCE = 12
BASELINE = '709b897'

# narrowText() in text-process-kr.py maps ASCII to these glyph slots for `^`
# entries. Anything not listed keeps its ordinary code point.
NARROW = {"a": 0x81, "b": 0x82, "c": 0x83, "d": 0x84, "e": 0x85, "f": 0x86, "g": 0x87,
          "h": 0x88, "k": 0x8A, "n": 0x8B, "o": 0x8C, "p": 0x8D, "q": 0x8E, "r": 0x8F,
          "s": 0x90, "t": 0x89, "u": 0x96, "v": 0x97, "x": 0x98, "y": 0x99, "z": 0x9A,
          "A": 0x9B, "B": 0x9C, "C": 0x9D, "D": 0x9E, "E": 0x9F, "F": 0xA0, "G": 0xA2,
          "H": 0xA3, "J": 0xA4, "K": 0xA5, "L": 0xA6, "O": 0xA7, "P": 0xA8, "Q": 0xA9,
          "R": 0xAC, "S": 0xAD, "U": 0xAE, "V": 0xAF, "X": 0xB0, "Y": 0xB1, "Z": 0xB2,
          " ": 0xBC}

_rom = open(BUILT, 'rb').read()


def advance(idx):
    ptr = struct.unpack_from('<I', _rom, DIALOG_FONT + idx * 4)[0]
    off = ptr - 0x08000000
    return _rom[off + 5] if 0 <= off < len(_rom) else 8


AW = {c: advance(c) for c in range(256)}

BREAK = re.compile(r'\[(?:N|NL|2NL)\]')
ENTRY = re.compile(r'^#\s*(0x[0-9A-Fa-f]+)\s*(\^?)\s*$')


def width(text, narrow):
    """Rendered px width of one display line; bracket codes are not drawn."""
    s = re.sub(r'\[[^\]\n]*\]', '', text)
    total = 0
    for ch in s:
        if ord(ch) >= 0x80:
            total += KR_ADVANCE
        else:
            total += AW[NARROW[ch]] if narrow and ch in NARROW else AW[ord(ch)]
    return total


def entries(src):
    """Yield (id, is_narrow, [display lines]) for one text file."""
    eid = None
    narrow = False
    body = []
    for line in src.splitlines():
        m = ENTRY.match(line.strip())
        if m:
            if eid:
                yield eid, narrow, body
            eid, narrow, body = m.group(1), m.group(2) == '^', []
        elif eid is not None:
            body.append(line)
    if eid:
        yield eid, narrow, body


def display_lines(body):
    for line in body:
        for seg in BREAK.split(line):
            seg = seg.strip()
            if seg:
                yield seg


def baseline_files():
    out = subprocess.run(['git', 'ls-tree', '-r', '--name-only', BASELINE, TEXT],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p.endswith('.txt')]


def show(path, rev):
    r = subprocess.run(['git', 'show', '%s:%s' % (rev, path)],
                       cwd=ROOT, capture_output=True, check=False)
    return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None


def main():
    report = []
    for path in baseline_files():
        old = show(path, BASELINE)
        try:
            new = io.open(os.path.join(ROOT, path), encoding='utf-8').read()
        except IOError:
            continue
        if old is None:
            continue

        # budget per (file, narrow-ness) from the widest original display line
        budget = {}
        samples = {}
        for _eid, narrow, body in entries(old):
            for seg in display_lines(body):
                w = width(seg, narrow)
                samples[narrow] = samples.get(narrow, 0) + 1
                if w > budget.get(narrow, 0):
                    budget[narrow] = w

        for eid, narrow, body in entries(new):
            cap = budget.get(narrow)
            if not cap:
                continue
            for seg in display_lines(body):
                w = width(seg, narrow)
                if w > cap:
                    report.append({'file': path, 'id': eid, 'narrow': narrow,
                                   'budget': cap, 'width': w, 'line': seg,
                                   'samples': samples[narrow]})

    narrow_hits = [r for r in report if r['narrow']]
    print('over-wide display lines: %d total, %d in narrow-font entries'
          % (len(report), len(narrow_hits)))
    by_file = {}
    for r in report:
        by_file.setdefault(r['file'], []).append(r)
    for path in sorted(by_file, key=lambda p: -len(by_file[p])):
        rs = by_file[path]
        print('\n%s  (%d)' % (path, len(rs)))
        for r in rs[:8]:
            # A budget drawn from only a handful of original lines is not the box
            # width -- it is just the longest of those few. Two entries were cut
            # for nothing that way (item names, stat labels) before this warned.
            weak = ' <- budget from only %d lines, check the box' % r['samples'] \
                if r['samples'] < 10 else ''
            print('   %s %s %3d/%3dpx  %s%s'
                  % (r['id'], 'narrow' if r['narrow'] else '      ',
                     r['width'], r['budget'], r['line'], weak))
        if len(rs) > 8:
            print('   ... %d more' % (len(rs) - 8))

    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '_narrow_overwide.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
