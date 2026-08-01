"""Report which target files are translated vs still English.
Refreshes _translate_remaining.json with the still-untranslated list.
Run from the Text/ directory:  python ../KoreanPatch/check_translation.py
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
full = json.load(open(os.path.join(HERE, '_translate_filelist.json'), encoding='utf-8'))

# Files whose remaining Latin text is intentional and reviewed, so the
# English-ratio heuristic can never clear them on its own.
ACCEPTED_AS_IS = {
    # contributor handles / usernames -- kept verbatim by convention
    'Credits.txt',
}

done, todo = [], []
for p in full:
    if not os.path.isfile(p):
        todo.append(p)
        continue
    txt = open(p, encoding='utf-8').read()
    has_kr = bool(re.search(r'[가-힣]', txt))
    eng = total = 0
    for ln in txt.splitlines():
        s = ln.strip()
        # '#'/'##' = entry tags, '//' = source comments -- neither is shown
        # to the player, so English there is not untranslated text.
        if not s or s.startswith('#') or s.startswith('//'):
            continue
        bare = re.sub(r'\[[^\]]*\]', '', s)
        letters = re.sub(r'[^A-Za-z]', '', bare)
        kr = re.search(r'[가-힣]', bare)
        if len(letters) >= 4 and not kr:
            eng += 1
        total += 1
    ratio = eng / max(1, total)
    # files with no translatable prose at all (empty, or only tags/#includes)
    # have nothing to do -- count them as done instead of flagging forever.
    (done if (total == 0 or p in ACCEPTED_AS_IS or (has_kr and ratio < 0.15))
     else todo).append(p)

json.dump(todo, open(os.path.join(HERE, '_translate_remaining.json'), 'w'),
          ensure_ascii=False, indent=0)
print('DONE: %d   REMAINING: %d' % (len(done), len(todo)))
print('remaining -> KoreanPatch/_translate_remaining.json')
for p in todo:
    print('  ', p)
