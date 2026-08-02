# Translation waves and verification

## Why waves

A full FE romhack script runs to thousands of strings. Splitting it into chunks
of ~120 and dispatching 4-6 subagents at a time keeps each agent's context small
enough that it can actually read the glossary and neighbouring chapters.

## Never overwrite existing work

When a chunk is partially translated, do **not** hand the whole chunk back out.
An agent that dies mid-write leaves you worse off than before.

Instead emit the gap only — the ids with no translation yet — and have the agent
write to a *new* file (`partNN_b.py`). If the build globs all part files and
later ones win, both files coexist and nothing is lost. Use the same trick for
repairs (`partNN_fix.py`) and for overrides.

Make the progress script merge those variants too, or it will keep reporting
completed chunks as partial.

## Verify their output yourself

Subagents report confidently and are sometimes wrong. Every wave in this project
produced at least one agent whose self-report was accurate and at least one bug
the agent didn't notice. Run an independent checker over each file:

- **parse** — valid Python/JSON and exposes the expected structure
- **coverage** — ids exactly match the input chunk, none missing or extra
- **encoding** — the whole file encodes to the ROM's charset (EUC-KR)
- **tokens** — control-token multiset matches the source, trailing terminator exempt
- **portrait** — leading `[slot][10][id]` run reproduced verbatim
- **alignment** — no entry's tokens match a *different* source id better than its own
- **leftovers** — no untranslated English prose

Exit non-zero on failure so it can gate a build. Then put the checker's command
**into the dispatch prompt** and tell the agent to iterate until it passes. That
change alone had agents self-correcting real defects: one caught 20 ids it had
missed because its file read was paginated, another fixed 21 line-count
mismatches, another found a speaker code that would have put a character's line
in someone else's voice.

## The misalignment failure mode

Watch for translations landing on the wrong id. One wave shifted a run by +2, so
one character's dialogue appeared in another's scene. The token guard happened to
catch it, but only by luck — a shifted pair with matching token counts would have
shipped silently.

Detect it by checking whether an entry's token sequence matches some *other*
source id exactly while not matching its own. Only apply this to entries that
already failed the token or portrait check: dialogue and village lines share
token shapes constantly, so matching another id means nothing on its own and
produces pure noise if you check every entry.

Put an explicit "keep every line under its OWN id, re-check id-by-id" instruction
in the dispatch prompt.

## Terminology consistency

Independent agents transliterate unlisted names independently, so the same
character becomes 구나르 in one chapter and 군나르 in the next. A player reads
those as two different people.

**Resolve by file spread, not raw count.** A spelling used once in eight chapters
reflects broader agreement than one used thirty times inside a single file —
that single file is one agent's opinion repeated.

Maintain an explicit watchlist of confirmed variant pairs and count them exactly;
that half is reliable. Automatic discovery is worth having but tune it for
precision: edit distance over inflected Korean is inherently noisy, and loosening
thresholds took one such tool from 4 findings to 254, nearly all ordinary
vocabulary. Strip postpositions before comparing (벨라로의/벨라로에/벨라로에서
are one rendering, not three), and treat a clean automatic pass as "nothing new
jumped out", never as "the corpus is consistent".

Fold decisions back into the glossary with the reasoning, so later waves don't
relitigate them. Include category rules, not just names — for instance "items are
translated by meaning (Dragonstone=용의 돌), spells are transliterated
(Fire=파이어)" prevents a whole class of drift.

## Don't let the checker dictate content

A verification heuristic should describe what's broken, not decide style. A
leftover-English check once pushed agents into Hangul-izing sound-test track
titles, because untranslated track names tripped it. Exempt the pattern instead,
and let a human make the content call.
