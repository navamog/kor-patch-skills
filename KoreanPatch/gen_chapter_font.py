# -*- coding: utf-8 -*-
"""Build the Korean glyph set for the chapter-title screen.

Chapter titles do not go through the text engine. EngineHacks/TMGC/ChapterNames
draws them from its own atlas: routine_20e8 maps a byte to a glyph index,
chartable[index*8] describes the glyph, and sub_80820CC finds it in the atlas by
summing the cell widths (+4) of every earlier entry, wrapping every 256px into
16px rows. So appending entries and packing the atlas in the same order is
enough -- no position needs to be stored.

This script emits, for the syllables actually used by ChapterNames.txt:
  font.kr.png     atlas: the original 66 ASCII glyphs, then the Hangul
  chartable.kr.dmp   extended 8-byte entries
  krtable.dmp     u16 codepoints, 0-terminated, searched by the patched routine

Index 128 is skipped: routine_20e8 returns 0x80 to mean "space", and the
callers compare against it, so no glyph may live at that index.

Run from repo root:
    python TMGC_Buildfiles/KoreanPatch/gen_chapter_font.py
"""
import io
import os
import re
import struct
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHDIR = os.path.join(ROOT, 'EngineHacks', 'TMGC', 'ChapterNames')
NAMES = os.path.join(ROOT, 'Text', 'ChapterNames.txt')

SRC_PNG = os.path.join(CHDIR, 'font.png')
SRC_TBL = os.path.join(CHDIR, 'chartable.dmp')
OUT_PNG = os.path.join(CHDIR, 'font.kr.png')
OUT_TBL = os.path.join(CHDIR, 'chartable.kr.dmp')
OUT_KR = os.path.join(CHDIR, 'krtable.dmp')

FONT = r"C:\Windows\Fonts\batang.ttc"
SIZE = 13
CELL = 16
SPACE_INDEX = 0x80
ATLAS_W = 256


def used_syllables():
    txt = io.open(NAMES, encoding='utf-8').read()
    body = [l for l in txt.splitlines() if l and not l.startswith('#')]
    joined = ''.join(re.sub(r'\[[^\]]*\]', '', l) for l in body)
    return sorted(set(c for c in joined if '가' <= c <= '힣'))


def main():
    syl = used_syllables()
    old = open(SRC_TBL, 'rb').read()
    n_old = len(old) // 8
    print('existing glyphs: %d   hangul needed: %d' % (n_old, len(syl)))

    # ---- assign indices, stepping over the space sentinel ----
    index_of = {}
    idx = n_old
    for ch in syl:
        if idx == SPACE_INDEX:
            idx += 1                      # leave a blank cell there
        index_of[ch] = idx
        idx += 1
    total = idx
    print('indices %d..%d (skipping 0x80), %d entries total' % (n_old, total - 1, total))

    # ---- chartable ----
    tbl = bytearray(old)
    for i in range(n_old, total):
        # left/right kern 0, advance = CELL, cell width = CELL,
        # drawn width = CELL, rows 0..CELL
        tbl += bytes([0, 0, CELL, CELL, CELL, CELL, 0, CELL])
    open(OUT_TBL, 'wb').write(bytes(tbl))
    print('wrote %s (%d bytes, %d entries)' % (os.path.basename(OUT_TBL), len(tbl), len(tbl) // 8))

    # ---- codepoint table for the patched routine ----
    kr = b''.join(struct.pack('<H', ord(c)) for c in syl) + b'\x00\x00'
    open(OUT_KR, 'wb').write(kr)
    print('wrote %s (%d codepoints)' % (os.path.basename(OUT_KR), len(syl)))

    # ---- atlas ----
    # x position of a glyph = sum of cell widths before it, wrapped at 256
    pos = []
    run = 0
    for i in range(total):
        pos.append(run)
        run += tbl[i * 8 + 4]
    height = ((run + ATLAS_W - 1) // ATLAS_W) * CELL
    src = Image.open(SRC_PNG)
    atlas = Image.new('P', (ATLAS_W, height), 0)
    atlas.putpalette(src.getpalette())
    atlas.paste(src.crop((0, 0, ATLAS_W, src.height)), (0, 0))

    # The original glyphs are bevelled: a white core (1) with a light edge (5)
    # up/left and a dark edge (8) down/right. Match that so Hangul does not look
    # flat beside the Latin.
    CORE, LIGHT, DARK = 1, 5, 8

    f = ImageFont.truetype(FONT, SIZE)
    ap = atlas.load()
    for ch, i in index_of.items():
        gx, gy = pos[i] % ATLAS_W, (pos[i] // ATLAS_W) * CELL
        mask = Image.new('L', (CELL, CELL), 0)
        d = ImageDraw.Draw(mask)
        bb = f.getbbox(ch)
        d.text(((CELL - (bb[2] - bb[0])) // 2 - bb[0],
                (CELL - (bb[3] - bb[1])) // 2 - bb[1] - 1), ch, fill=255, font=f)
        m = [[mask.getpixel((x, y)) >= 128 for x in range(CELL)] for y in range(CELL)]

        def put(x, y, v):
            if 0 <= x < CELL and 0 <= y < CELL:
                ap[gx + x, gy + y] = v

        for y in range(CELL):
            for x in range(CELL):
                if not m[y][x]:
                    continue
                put(x + 1, y + 1, DARK)     # shadow first
        for y in range(CELL):
            for x in range(CELL):
                if not m[y][x]:
                    continue
                put(x - 1, y - 1, LIGHT)    # then highlight
        for y in range(CELL):
            for x in range(CELL):
                if m[y][x]:
                    put(x, y, CORE)         # core on top
    atlas.save(OUT_PNG)
    print('wrote %s (%dx%d)' % (os.path.basename(OUT_PNG), ATLAS_W, height))


if __name__ == '__main__':
    main()
