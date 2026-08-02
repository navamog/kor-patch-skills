# Checkers

Working code from a shipped FE8U buildfile-rebuild patch. They are **starting
points, not drop-ins** — paths, the baseline commit, the font address and the
Hangul advance are all project-specific and sit in constants near the top of
each file. Read them before running.

| Script | Catches |
|---|---|
| `check_line_width.py` | lines too wide for their box — the engine drops them, so nothing else sees this |
| `check_narrow_width.py` | the same, for `^` narrow-font entries, which `check_line_width.py` cannot see |
| `verify_entries.py` | dropped entries and dropped bracket codes between the original and the translation |
| `find_unoverridden.py` | ids the build never redefines, which keep the vanilla English |

## check_line_width.py

Derives the budget from the widest line in the pre-translation commit rather
than guessing at box geometry, pulls ASCII advances from the real font in the
clean ROM, and splits on `[N]`/`[NL]`/`[2NL]` so a mid-line break counts as two
rows. Writes `_overwide_lines.json` for a repair pass to consume.

**It cannot see `^` narrow-font entries** — it reads advances from the clean ROM,
where the hack's narrow glyphs do not exist, so it falls back to 8px against a
real 4-5px and inflates those budgets ~2x. Use `check_narrow_width.py` for them.

Give each surface its own copy with its own budget — a guide or journal panel is
narrower than a dialogue box, and checking it against the dialogue budget reports
zero while text is visibly cut off.

## verify_entries.py

Compares each file against its pre-translation self and reports:

- **damage** — an entry tag vanished, or the bracket-code *multiset* changed.
  Agents drop `[...]` and `[N]` while reporting "byte-identical", so run this
  yourself rather than trusting their self-checks.
- **benign reflow** — same codes, different order. Korean word order legitimately
  moves an `[OpenQuote]…[CloseQuote]` pair across an `[N]`; do not flag it.

Note the multiset is per file. Moving a code between two entries in the same file
passes — tighten to per entry if that matters for your project.

## find_unoverridden.py

Diffs the ids the build installs (`setText($ID, …)`) against every id in the ROM
dump. Everything missing keeps the original game's English no matter what you do
to the script files; fixing one means adding a new entry with the same id.

Expect a long tail of vanilla story strings the hack never shows. Filter to
entries with real prose before deciding anything is a problem.

## check_narrow_width.py

Same idea, fixed for the narrow font: advances come from the **built** ROM (the
hack installs glyph slots 0x81-0xBC; the clean ROM has nothing there), and `^`
entries are measured through `narrowText()`'s own mapping.

It derives a separate budget per (file, narrow-ness) so a file mixing both kinds
does not judge one against the other's box.

Watch for degenerate budgets: if only two or three entries in a file are
non-narrow, the budget is just the longest of those few, and short item names get
flagged against a box that is really much wider. Check what a budget was derived
from before cutting anything.
