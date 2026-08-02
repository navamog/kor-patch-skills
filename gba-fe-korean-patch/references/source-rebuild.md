# When the hack ships its buildfiles

Some romhacks publish their source (TMGC, for example). Then you don't patch a
compiled ROM — you clone the buildfiles, translate the script in place, add your
own engine hooks, and rebuild against a clean ROM. Different workflow, different
failure modes from binary hacking.

## The population is not "the files you were given"

Three separate times, work reported as 100% complete was not:

**The root buildfile has its own inline entries.** `text_buildfile.txt` looked
like a list of `#include`s. It also held 79 inline entries — difficulty
descriptions, the whole config menu, prep-screen help, terrain names — and it was
absent from the translation file list. Every report said 121/121 done while those
stayed English. **The root file is a translation target too.**

**Strings the buildfile never defines keep the vanilla text.** The hack only
redefines the message ids it changed; everything else falls through to the
original game's English. Editing `Text/` cannot reach them — you have to add a
*new entry with the same id*.

Diff the ids the build installs against the full ROM dump:

```
setText($ID, …) lines in the generated installer  ->  the ids you override
every id in the ROM dump                          ->  the ids that exist
```

In one project that left **1,723** un-overridden entries, including every
level-up message, the unit action menu (Item/Supply/Wait), the stat screen
labels, and the whole unit-menu help text. Filter to ones with real prose and
ignore the vanilla story leftovers the hack never shows.

**Empty files and `//` comments are not untranslated.** A completeness heuristic
that counts Latin characters will flag files that are legitimately empty, files
that are only dev comments, and credits full of contributor handles. Give it an
explicit accepted-as-is list or it can never reach zero.

## Count the hooks

Hooking "the four text functions" was not enough. FE8 has additional entry points
that walk a string **one byte at a time** (`ldrb r0,[r4]` / `add r4,#1`) and look
up `glyphs[byte]` directly — nothing routed through them can render UTF-8.

Disassemble each candidate before hooking it and confirm the arguments match the
counterpart you already replaced; if they do, the same replacement drops in.
Eight hooks, not four, in this engine.

## Subsystems with their own font

Not everything draws through the text engine. Chapter titles had a private stack:
its own variable-width atlas, its own `chartable[index*8]`, and its own THUMB
routine. Korean simply didn't exist in it, so the screen was blank.

Two things made this tractable, and both are worth checking before you start:

- **Is the routine's source in the tree?** Reassemble it untouched first and
  confirm it reproduces the shipped binary byte-for-byte. That gate tells you
  patching is safe.
- **How does it locate a glyph?** Here a helper summed the *cell widths of every
  earlier entry*, wrapping every 256px. Nothing stored a position — so appending
  entries and packing the atlas in the same order was enough.

**The buffer is the real constraint.** The atlas was exactly 256x64 = 8192 bytes
because the font is LZ77-decompressed into a shared 8KB scratch buffer. A Korean
atlas needs far more, and the bigger decompress ran 20KB past the buffer and
killed the game in the BIOS exception vector. The fix was to stop decompressing:
store the atlas uncompressed and point the draw routine at it in ROM, since it
only ever reads. That removes the limit instead of working around it.

When you patch a hand-written routine, preserve every register the original
didn't touch — the Korean path here needed a scratch register the callers
expected to survive.

## Verify the tools, not just the output

**Reproduce before you replace.** Before regenerating any `.dmp`, run the tool on
the *untouched* source and check it reproduces the shipped file byte-for-byte. If
it doesn't, your regeneration is a second variable.

**Indexed-PNG palettes carry the indices.** A PNG written with an all-black
palette makes every colour identical, the converter collapses the sheet to index
0, and the art silently vanishes from the screen — with no build error. Give the
image 16 distinct palette entries, and round-trip the compressed output back to
the pixels you drew.

**Do not type Korean as `\uXXXX` escapes.** Four words shipped wrong that way
(늑지 for 늪지, 훃불 for 횃불). Type the Hangul directly and read the rendered
file back.

## Emulator file locks

A running emulator memory-maps the ROM, and the build then fails with a
permission error that has nothing to do with permissions
("user-mapped section open"). Build to a second filename rather than killing the
user's emulator — they may be mid-test.

## Retract wrong theories out loud

A whole root-cause analysis here rested on a control-code prefix belonging to an
engine that was **commented out of the build**. The file was in the tree, the
source read convincingly, and none of it was in the ROM.

Before theorising about a subsystem, confirm it is actually installed — grep the
master installer for the include, and read the bytes at the address it claims to
hook.
