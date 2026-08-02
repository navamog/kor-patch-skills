# Worked case: one title screen, twelve broken builds

The value here is the *order* the mistakes were made in, because each one made
the next one harder to see. Roughly a dozen builds shipped visibly broken.

## What was being attempted

Replace the English title logo with Korean, add a Korean subtitle, and put a
translation credit in a corner. Three surfaces, and they turned out to be three
different mechanisms.

## The sequence

**1. Logo drawn, colours wrong.** Shapes correct, colours streaked. Four
attempts followed — different font, different shadow construction, auto-fitting
the text — each plausible, each aimed at the art. The cause was the compressor
emitting displacement-1 back-references, which `LZ77UnCompVram` cannot decode.
The tell that was ignored for too long: **the data read back from the ROM was
perfect**, and the project's own decoder round-tripped it. Only dumping VRAM and
comparing against what was written found it.

*Cost: four builds. Avoidable by: the null control (re-encode the original and
patch it in) on the first failure.*

**2. Subtitle attempt one — blanked the strip.** Wrote the Korean and left the
other pixels at index 0. A black band appeared across the artwork, because on
that layer index 0 draws as backdrop, and because the strip's tiles held the
scenery as well as the letters.

**3. Subtitle attempt two — reconstructed the plate.** Sampled the rows above
and below to rebuild what was behind the text. Came back striped: the map there
named tiles past the end of the tile area, so half the reconstruction was
backdrop.

**4. Subtitle attempt three — filled silhouette.** Different shadow shape.
Irrelevant to the actual problem; the strip was still being blanked.

**5. Credit attempt — searched for free tiles.** Found a "free" run using the
map stored inside the data block. Black holes appeared elsewhere on screen,
because a second layer shared the same character area at a different bit depth.
Fixed that, and holes still appeared — because the block's map was deduplicated
and its plain tiles were reused 11 to 38 times each.

**6. Credit position would not move.** Column 0, 19, 10, 1 — the text appeared
at x≈73 every time. Three of those moves were driven by a measurement taken by
scanning the screenshot for bright pixels, which was picking up the sword hilt.

**7. An offline checker was written** to assert nothing changed outside the
intended box. It passed. The build was visibly broken. The checker read the
map the same way the writer did, so it could only ever confirm a consistent
mistake.

## What actually resolved it

The null control. Re-encoding the untouched background block and patching it in
produced a perfect screen — which retired the compressor as a suspect for that
block and left exactly one candidate: the map.

Reading the map from **VRAM** rather than from the block showed it was linear
(`0, 1, 2, 3 …`). That single fact explained every prior symptom at once:

- `tile = row * 30 + col`, so tile 39 is row 1 column 9, i.e. x=72 — the fixed
  position the credit kept returning to.
- Every tile is on screen exactly once, so there were never any free tiles.
- The "free" tiles that had been claimed were live artwork, which is what the
  black holes were.

After that: compute tiles from the linear map, composite in place, never touch
the map. It worked first try. The subtitle followed the same day, once the
lettering was separated from the artwork by palette (every warm index was
lettering; the scenery-only band contained none).

## The lessons, ranked by what they would have saved

1. **Run the null control at the first unexplained failure.** It is one build
   and it halves the search space. Skipping it cost most of the twelve.
2. **Read the map from VRAM before writing any map.** The map in the block may
   be decoration.
3. **A verifier built on the edit's own assumptions verifies nothing.** If you
   write one, feed it a deliberately broken input and confirm it fails.
4. **Do not measure screen positions by scanning for bright pixels.** Artwork
   has highlights. Measure from the tiles, or crop and look.
5. **When three fixes in a row miss, stop fixing and go measure.** The third
   failed fix is the signal that the model is wrong, not the art.
