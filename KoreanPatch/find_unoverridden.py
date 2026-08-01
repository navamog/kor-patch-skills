# -*- coding: utf-8 -*-
"""Find ROM text entries that are still English because no buildfile
entry overrides them.

The hack only replaces the message IDs it defines; every other ID keeps the
vanilla FE8 string. Those show up in-game in English (Unit / Status /
Options / End / NO DATA ...) and no amount of editing Text/ fixes them --
they need a NEW entry with that ID.

setText($ID, label) lines in InstallTextData.event are the authoritative
list of overridden IDs.

Run from repo root:  python TMGC_Buildfiles/KoreanPatch/find_unoverridden.py
"""
import io, json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEXT = os.path.join(ROOT, 'TMGC_Buildfiles', 'Text')

installer = io.open(os.path.join(TEXT, 'InstallTextData.event'), encoding='utf-8', errors='replace').read()
overridden = {int(m, 16) for m in re.findall(r'setText\(\$([0-9A-Fa-f]+)\s*,', installer)}
print('overridden IDs: %d' % len(overridden))

dump = io.open(os.path.join(TEXT, 'textdump.txt'), encoding='utf-8', errors='replace').read()

entries = []
cur_id = None
buf = []
for line in dump.splitlines():
    m = re.match(r'^#\s*(0x[0-9A-Fa-f]+)', line)
    if m:
        if cur_id is not None:
            entries.append((cur_id, '\n'.join(buf)))
        cur_id = int(m.group(1), 16)
        buf = []
    elif cur_id is not None:
        buf.append(line)
if cur_id is not None:
    entries.append((cur_id, '\n'.join(buf)))

print('dump entries: %d' % len(entries))

missing = []
for eid, body in entries:
    if eid in overridden:
        continue
    bare = re.sub(r'\[[^\]]*\]', '', body).strip()
    if not bare:
        continue
    letters = re.sub(r'[^A-Za-z]', '', bare)
    if len(letters) < 2:
        continue
    missing.append((eid, ' '.join(bare.split())[:70]))

print('un-overridden entries with English text: %d\n' % len(missing))
for eid, s in missing[:80]:
    print('  0x%04X  %s' % (eid, s))

json.dump([{'id': '0x%04X' % e, 'text': s} for e, s in missing],
          io.open(os.path.join(os.path.dirname(__file__), '_unoverridden.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nfull list -> KoreanPatch/_unoverridden.json')
