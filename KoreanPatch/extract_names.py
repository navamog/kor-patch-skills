"""Extract proper-noun candidates (character/boss/place names) from the
name-list source files for glossary building. Emits a TSV of unique names."""
import os, re, glob

TEXT = os.path.join(os.path.dirname(__file__), '..', 'Text')
NAME_FILES = ['UnitNames.txt', 'Bosses.txt', 'EventViewerNames.txt',
              'TheReturnNames.txt']

names = {}
# entries look like:  ##Name_Xxx  \n  Blair[X]
for fn in NAME_FILES:
    path = os.path.join(TEXT, fn)
    if not os.path.exists(path):
        continue
    lines = open(path, encoding='utf-8').read().splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r'##Name_(\w+)', ln.strip())
        if m and i + 1 < len(lines):
            val = lines[i + 1].strip()
            val = re.sub(r'\[[^\]]*\]', '', val).strip()
            if val and re.match(r"^[A-Za-z][A-Za-z '\-]*$", val):
                names.setdefault(val, set()).add(fn)

# place/faction names harvested from chapter names + boss descs
places = set()
for fn in ['ChapterNames.txt', 'ChapterNarrations.txt', 'Bosses.txt']:
    path = os.path.join(TEXT, fn)
    if not os.path.exists(path):
        continue
    txt = open(path, encoding='utf-8').read()
    for w in re.findall(r"\b([A-Z][a-z]+(?:'[a-z]+)?(?:ian|ese|stran|aron|ese)?)\b", txt):
        if len(w) > 4:
            places.add(w)

out = os.path.join(os.path.dirname(__file__), 'glossary_candidates.tsv')
with open(out, 'w', encoding='utf-8') as f:
    f.write('# type\tenglish\tkorean(fill in)\tsources\n')
    for n in sorted(names):
        f.write('name\t%s\t\t%s\n' % (n, ','.join(sorted(names[n]))))
    for p in sorted(places - set(names)):
        f.write('place?\t%s\t\t\n' % p)

print('names:', len(names), 'place-candidates:', len(places))
print('->', out)
