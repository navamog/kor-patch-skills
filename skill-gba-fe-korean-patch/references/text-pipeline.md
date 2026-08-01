# Text table, tokens, encoder, guards

## The table

FE8U keeps a pointer table (0x1024D7C in the ROM this was derived from) with
0x7FFF entries. Bit 31 set means the string is stored uncompressed; clear means
Huffman-compressed with a tree elsewhere in the ROM.

**Most of the table is padding.** In the observed ROM only ids below ~0x14C3
carry real content; the remaining 27,452 entries all point at one shared empty
string. Before concluding you have a dump gap, check whether the "missing" ids
share a single pointer target — that is what unused looks like, and it will save
you from chasing a non-problem. Conversely, ids that decode to `--` are real
placeholder entries, not failures.

## Control tokens

Dump control bytes as bracket tokens so translators can preserve them:

| Token | Byte | Meaning |
|---|---|---|
| `[X]` | 0x00 | segment end / terminator |
| `[NL]` | 0x01 | line break |
| `[A]` | 0x03 | page advance (wait for A) |
| `[10][HH]` | 0x10 HH | portrait command **plus a one-byte argument** |
| `[80HH]` | 0x80 HH | runtime-substituted value (item name, gold, unit name) |

Two traps here, both of which shipped bugs:

**`[80HH]` is four hex digits.** A token regex written as `[0-9A-Fa-f]{2}`
silently fails to match it, so the encoder falls through to the text branch and
writes the literal ASCII characters `[8022]` into the ROM. On screen the discard
prompt reads "[8022]을(를) 버릴까요?". Match the 4-digit form **before** the
2-digit form. This affected 452 strings and the guard could not see it, because
the guard used the same regex — so both sides agreed the string was fine. **When
you change a token regex, change it in the encoder and in every checker at
once.**

**`[10]`'s argument may be a printable character.** Portrait ids like `\`, `"`,
`k`, `%` appear as ordinary characters after the token. A parser that stops at
the first non-token character truncates the portrait run and misreads the
string. Consume one byte after every `[10]`.

`[X]` behaves differently per space: in the story bank every entry ends with
exactly one trailing `[X]` and none appear mid-string, while system-space entries
use it mid-string freely. Don't generalise a rule from one space to the other.

## Encoder

Convert tokens to control bytes and text to EUC-KR. Append a terminator when the
encoded record doesn't already end in one.

That auto-append has a useful consequence: **a translation that merely omits the
trailing `[X]` encodes to identical bytes**, so the guard should exempt it
rather than reject the line. In this project that exemption alone recovered 19
correct translations that were shipping in English.

## Guards

Guards are what keep a broken line from reaching a player. Each of these was
added after the corresponding bug shipped.

**Token multiset guard.** If the control-token multiset differs from the source,
keep the original string. Catches dropped `[NL]`/`[A]`/`[X]`, which otherwise
merge or truncate dialogue. Compare multisets, not sequences — Korean word order
legitimately moves `[X]`/`[80xx]` around ("Throw away [X][8022]?" becomes
"[X][8022]을(를) 버릴까요?"), so an order-sensitive check produces mostly false
positives in system space.

**Portrait prologue guard.** The leading `[slot][10][id]` run is scene state —
who stands on which side — not wording. A multiset guard cannot see a swapped
slot, so compare that run byte for byte. This caught a support conversation
shipping with the two portraits reversed, and two strings whose portrait
argument byte had been eaten by backslash escaping.

**Structural check for any path that bypasses the guards.** If some strings are
supplied as pre-built bytes rather than token strings, they skip the guard
entirely. That is exactly how the opening scene shipped with 13 of its 55 pages —
the renderer hit the terminator early and jumped to the next event. Decode such
records back into tokens and apply the same check.

## Coverage and effective mapping

Two counting rules, each learned the hard way:

**Count against the whole dump.** A per-chunk progress script only knows about
the chunks it was given. 254 system-space strings — menu commands like Talk,
Skills and Supply, plus weapon, skill and class names — were never handed to any
translator while the script reported zero remaining. Only in-game inspection
revealed it.

**Resolve overwrite order before judging.** When the build loads many part files
and later ones win, a per-file audit keeps reporting entries a later file already
fixed. Build the effective id→string map first, then check. Note also that load
order may not be alphabetical across groups: if the build reads all `sys_*` files
before all `story_*` files, an override placed in a `sys_*` file will be beaten
by any `story_*` file defining the same id.

## Auditing for dropped content

Beyond the guards, run a whole-population audit comparing each shipped string to
its source:

- `[A]` count mismatch — whole pages missing
- `[NL]` count mismatch — lines missing
- a stray terminator mid-record — everything after it is unreachable
- an English text run whose Korean counterpart is empty

The last one needs care: when token sequences match, text runs align 1:1, so a
blank counterpart means dropped text. But Korean word order legitimately empties
a run in fragment strings ("Got " + value + " gold." → the first fragment becomes
empty and the last carries "골드 획득"), and sources sometimes split a word
mid-token. Expect false positives there and check them individually rather than
trusting the count.

A raw length-ratio heuristic is nearly useless for Korean: at a 40% threshold it
flagged 125 perfectly complete descriptions, because Korean simply runs 40-50%
the character count of English.
