"""Verify each translated Text file still has the same entry tags as the
original (git HEAD). Catches agents that dropped or renamed entries.

Run from repo root:  python TMGC_Buildfiles/KoreanPatch/verify_entries.py
Writes _damaged_files.json with the list needing re-translation.
"""
import json, os, re, subprocess, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = 'TMGC_Buildfiles/Text'


def tags(text):
    """Entry tags: '##Name' definitions and '# 0xID' numeric entries."""
    out = []
    for ln in text.splitlines():
        s = ln.rstrip()
        if s.startswith('##'):
            out.append(s.strip())
        elif re.match(r'^#\s*0x[0-9A-Fa-f]+', s):
            out.append(re.sub(r'\s+', ' ', s.strip()))
    return out


def codes(text):
    """Bracket control codes ([X] [N] [OpenRight] [Blair] ...) in order.

    Only English prose is translated, so every code must survive. The
    *multiset* is the hard invariant -- a missing [X]/[N]/[...] or a
    translated control code is damage that tag counting cannot see.

    Order is only a warning: Korean word order legitimately moves a
    [OpenQuote]..[CloseQuote] pair across a [N] line break, which changes
    the sequence while preserving every code.
    """
    return re.findall(r'\[[^\]\n]*\]', text)


def git_show(path):
    try:
        return subprocess.run(['git', 'show', 'HEAD:' + path], cwd=ROOT,
                              capture_output=True, check=True).stdout.decode('utf-8', 'replace')
    except subprocess.CalledProcessError:
        return None


files = json.load(open(os.path.join(HERE, '_translate_filelist.json'), encoding='utf-8'))
damaged, ok, skipped, reordered = [], [], [], []

for rel in files:
    disk = os.path.join(ROOT, TEXT, rel)
    if not os.path.isfile(disk):
        skipped.append(rel)
        continue
    orig = git_show(TEXT + '/' + rel.replace('\\', '/'))
    if orig is None:
        skipped.append(rel)
        continue
    cur = open(disk, encoding='utf-8').read()
    a, b = tags(orig), tags(cur)
    ca, cb = codes(orig), codes(cur)
    lost = Counter(ca) - Counter(cb)
    gained = Counter(cb) - Counter(ca)

    if a == b and not lost and not gained:
        ok.append(rel)
        if ca != cb:
            reordered.append(rel)
        continue

    missing = [t for t in a if t not in b]
    extra = [t for t in b if t not in a]
    d = {'file': rel, 'orig_tags': len(a), 'cur_tags': len(b),
         'missing': missing[:5], 'missing_count': len(missing),
         'extra': extra[:5], 'code_diff': None}
    if lost or gained:
        d['code_diff'] = 'codes %d -> %d; lost %s; gained %s' % (
            len(ca), len(cb),
            dict(lost) or '{}', dict(gained) or '{}')
    damaged.append(d)

json.dump([d['file'] for d in damaged], open(os.path.join(HERE, '_damaged_files.json'), 'w'),
          ensure_ascii=False, indent=0)
print('OK: %d   DAMAGED: %d   SKIPPED: %d   (code-order reflow, benign: %d)'
      % (len(ok), len(damaged), len(skipped), len(reordered)))
for d in damaged:
    print('  %-55s tags %d -> %d  (missing %d)' % (d['file'], d['orig_tags'], d['cur_tags'], d['missing_count']))
    if d['missing']:
        print('      e.g. missing:', ', '.join(d['missing'][:3]))
    if d['extra']:
        print('      e.g. extra  :', ', '.join(d['extra'][:3]))
    if d['code_diff']:
        print('      %s' % d['code_diff'])
print('\ndamaged list -> KoreanPatch/_damaged_files.json')
