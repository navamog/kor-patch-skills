# Not going in circles

The expensive part of a long romhack is rarely the fix. It is the hours spent
reasoning correctly from a false premise. These are the premises that failed.

## Validate the instrument before believing its negatives

Seven memory breakpoints in a row failed to fire while hunting a render loop.
Each miss was treated as a fact about the game, and three conclusions were built
on top of them: "not this font table", "not any of the four", "therefore the UI
has a private font". All three were unsupported — the last breakpoint had been
placed on a helper that *must* execute whenever Korean is drawn, and it did not
fire either.

**A run of negatives from one instrument is one observation about the
instrument, not N observations about the system.** Before trusting a negative,
point the instrument at something guaranteed to trigger. If that does not fire,
stop investigating the game.

Check the address space too: emulators often expose several memory views
(`gbaMemory` for the CPU bus, `gbaPrgRom` for cartridge offsets). A breakpoint
in the wrong view is silently never hit.

## A positive result you already have beats a negative you are hunting

While chasing "does this renderer read our data", the answer was already on
screen: the text had *changed* from English to garbled Korean when the patch
changed. That single positive proved the data path, and it outranked every
breakpoint that failed to fire.

Look for what already changed before instrumenting what might.

## Localised, self-correcting corruption is a desync

A run of wrong glyphs that snaps back to correct text is not bad glyph data. It
is a parser losing sync and re-finding it. Check whether a byte in one role can
be mistaken for a byte in another — in a two-byte encoding, whether any trail
byte can reach the lead-byte threshold.

Corollary: if the ROM bytes, the pointer, the glyph table and the bitmaps all
verify correct and the screen is still wrong, stop re-verifying the data. Some
*other* pass is reading it.

## Never measure while something else is writing

A build run mid-way through a batch of file-writing agents reported one
verifier failure and nine over-wide lines. Re-running the same command seconds
later, with no edit in between, gave zero and zero. The tell was a count that
differed between two runs of the identical command.

Two agents later independently reported a file as "shipping broken" for the same
reason. Checking cost one command; acting would have meant repairing ten
problems that never existed.

Quiesce the writers, then measure.

## A check that shares the edit's assumptions cannot catch the edit

A repair file whose name sorted before the file it meant to override was
silently discarded — and reported `OK`, because the verifier checked the
*winning* text rather than the file's own. Guard it explicitly: if an override
file ships none of its entries, it overrides nothing, and that is always a bug.

Note the asymmetry — a *base* file being fully superseded is normal and must not
warn, or the check drowns in false alarms.

## Find the cheapest screen that shows the symptom

Reproducing a chapter-title bug by replaying a prologue cost several attempts and
a large amount of time. The same string was reachable in **three taps** from
boot through a save-slot menu.

Before the second reproduction, ask where else this data is displayed. And take
a savestate immediately before any transient screen — title cards flash past and
are trivially missed on a fast-forward.

## Verify the artefact you are shipping, not the one you built

For release, apply the patch you are about to distribute and hash the *result*.
Hashing the build you happen to have on disk proves nothing about whether the
patch reproduces it.

Same for a compressor: round-trip the encoded block back through the decoder and
compare, before it ever reaches the console.

## Count before you overrule a table

When evidence conflicts with a recorded decision, count occurrences across the
whole corpus and write the numbers down. "This scene reads differently" is one
data point; a table built from thirty is not overturned by one.

Two useful refinements, both learned the hard way:

- **An apparent inconsistency may be a rule.** A character's register split by
  *setting* (formal vs private), not by error. Unifying it would have been wrong.
- **The minority may explain itself.** Three outliers all turned out to be the
  same scene type, which supported the majority reading rather than undermining it.

And when a count is close — two against, one for — say so and leave the table
alone rather than flipping it on a coin toss.
