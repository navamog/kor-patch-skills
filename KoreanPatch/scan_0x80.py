# -*- coding: utf-8 -*-
"""Census of Korean characters whose UTF-8 encoding contains byte 0x80.

0x80 is the Text_Engine_Rework control-code prefix ([0x80][0x26][XX] etc.),
so the dialogue interpreter -- which scans bytes without UTF-8 awareness --
mistakes such a byte for the start of a command, desyncs, and eats the
following bytes. Symptom: garbled glyphs mid-line, or the rest of the line
vanishing entirely.

A 3-byte UTF-8 sequence has 0x80 when:
  byte3 == 0x80  <->  (cp & 0x3F) == 0        e.g. 가 은 와 대
  byte2 == 0x80  <->  ((cp >> 6) & 0x3F) == 0

Run from repo root:  python TMGC_Buildfiles/KoreanPatch/scan_0x80.py
"""
import io, json, os, re, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEXT = os.path.join(ROOT, 'TMGC_Buildfiles', 'Text')


def bad_bytes(ch):
    """Return which byte positions of ch's UTF-8 encoding equal 0x80."""
    b = ch.encode('utf-8')
    return [i for i, v in enumerate(b) if v == 0x80]


def scan():
    per_file = Counter()
    per_char = Counter()
    entries = Counter()
    examples = []
    total = 0

    for dirpath, _, names in os.walk(TEXT):
        if '.TextEntries' in dirpath:
            continue
        for n in sorted(names):
            if not n.endswith('.txt'):
                continue
            path = os.path.join(dirpath, n)
            rel = os.path.relpath(path, TEXT).replace('\\', '/')
            cur_entry = None
            hit_entries = set()
            for ln_no, line in enumerate(io.open(path, encoding='utf-8', errors='replace'), 1):
                s = line.rstrip('\n')
                if s.startswith('#'):
                    cur_entry = s.strip()
                    continue
                for ch in s:
                    if ch < '':
                        continue
                    pos = bad_bytes(ch)
                    if not pos:
                        continue
                    total += 1
                    per_file[rel] += 1
                    per_char[ch] += 1
                    hit_entries.add((rel, cur_entry))
                    if len(examples) < 12:
                        examples.append((rel, ln_no, cur_entry, ch, s.strip()[:46]))
            for e in hit_entries:
                entries[e] += 1
    return per_file, per_char, entries, examples, total


per_file, per_char, entries, examples, total = scan()

print('=' * 70)
print('0x80-bearing Korean characters in built text')
print('=' * 70)
print('occurrences : %d' % total)
print('entries hit : %d' % len(entries))
print('files hit   : %d / %d' % (len(per_file), sum(1 for _ in per_file)))
print()
print('--- most frequent offending characters ---')
for ch, c in per_char.most_common(20):
    b = ch.encode('utf-8')
    print('  %s  U+%04X  %s   x%d' % (ch, ord(ch), b.hex(' ').upper(), c))
print()
print('--- worst files ---')
for f, c in per_file.most_common(15):
    print('  %-52s %d' % (f, c))
print()
print('--- examples ---')
for rel, ln, ent, ch, s in examples:
    print('  %s:%d  %s  [%s]' % (rel, ln, ent or '?', ch))
    print('      %s' % s)

json.dump({'total': total, 'entries': len(entries),
           'chars': {c: n for c, n in per_char.most_common()},
           'files': dict(per_file)},
          io.open(os.path.join(os.path.dirname(__file__), '_scan_0x80.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nreport -> KoreanPatch/_scan_0x80.json')
