.thumb

@ ============================================================
@ TMGC Korean text engine — UTF-8 aware replacements for the
@ four FE8U text primitives. Korean codepoints are looked up
@ arithmetically in contiguous glyph blocks (KRGlyphs_Dialog /
@ KRGlyphs_Menu). Everything else falls back to the vanilla
@ single-byte glyphs[] path, so ASCII + NarrowFont still work.
@
@ Glyph record = vanilla FE8 Glyph struct (0x48 bytes):
@   +0 next(u32) +4 hi(u8) +5 width(u8) +6 pad +8 16*u32 2bpp
@
@ Block index layout (see gen_font.py):
@   [0        .. 11171] U+AC00..U+D7A3 syllables
@   [11172    .. 11265] U+3131..U+318E compat jamo
@   [11266    ..      ] KRExtraTable order (0-terminated short list)
@ ============================================================

.equ gActiveFontPtr, 0x02028E70
@ font->glyphs base for the UI/menu font. This is compared against the live
@ font->glyphs, which is a GBA bus address -- it MUST carry the 0x08000000 ROM
@ base. Without it the compare never matched, every menu silently fell through
@ to the dialogue block, and Korean drew at 12px advances inside layouts built
@ for the 11px menu font: overlapping glyphs and text pushed out of its box.
.equ MENU_GLYPHS,    0x0858C7EC
.equ DIALOG_GLYPHS,  0x0858F6F4   @ (confirmed live at gActiveFont->glyphs)
.equ GLYPH_SIZE,     0x48
.equ JAMO_OFF,       11172
.equ EXTRA_OFF,      11266

.global KR_GetStringTextLen
.global KR_GetCharTextLen
.global KR_DrawString
.global KR_DrawCharacter
.type KR_GetStringTextLen, %function
.type KR_GetCharTextLen, %function
.type KR_DrawString, %function
.type KR_DrawCharacter, %function

@ ------------------------------------------------------------
@ UTF8_Decode: r0 = char* -> r0 = codepoint, r1 = byte length
@ (does not advance caller pointer)
@ ------------------------------------------------------------
.thumb_func
UTF8_Decode:
    push    {r4, lr}
    ldrb    r2, [r0]            @ b0
    cmp     r2, #0x80
    bcc     .Ldec_one
    mov     r3, #0xE0
    and     r3, r2
    cmp     r3, #0xC0
    beq     .Ldec_two
    mov     r3, #0xF0
    and     r3, r2
    cmp     r3, #0xE0
    beq     .Ldec_three
.Ldec_one:                      @ <0x80 or 4-byte/invalid -> 1 raw byte
    mov     r0, r2
    mov     r1, #1
    pop     {r4, pc}
.Ldec_two:
    ldrb    r1, [r0, #1]        @ b1
    mov     r3, #0x1F
    and     r3, r2
    lsl     r3, r3, #6
    mov     r4, #0x3F
    and     r4, r1
    orr     r3, r4
    mov     r0, r3
    mov     r1, #2
    pop     {r4, pc}
.Ldec_three:
    ldrb    r3, [r0, #1]        @ b1
    ldrb    r4, [r0, #2]        @ b2
    mov     r1, #0x0F
    and     r1, r2              @ b0 & 0x0F
    lsl     r1, r1, #12
    mov     r2, #0x3F
    and     r2, r3
    lsl     r2, r2, #6
    orr     r1, r2
    mov     r2, #0x3F
    and     r2, r4
    orr     r1, r2              @ r1 = cp
    mov     r0, r1
    mov     r1, #3
    pop     {r4, pc}

@ ------------------------------------------------------------
@ KR_Index: r0 = codepoint -> r0 = block index, or -1 if not KR
@ ------------------------------------------------------------
.thumb_func
KR_Index:
    push    {r4, r5, lr}
    ldr     r1, =0xAC00
    cmp     r0, r1
    bcc     .Lidx_notsyl
    ldr     r2, =0xD7A3
    cmp     r0, r2
    bhi     .Lidx_notsyl
    sub     r0, r0, r1          @ cp - 0xAC00
    pop     {r4, r5, pc}
.Lidx_notsyl:
    ldr     r1, =0x3131
    cmp     r0, r1
    bcc     .Lidx_extra
    ldr     r2, =0x318E
    cmp     r0, r2
    bhi     .Lidx_extra
    sub     r0, r0, r1          @ cp - 0x3131
    ldr     r1, =JAMO_OFF
    add     r0, r0, r1
    pop     {r4, r5, pc}
.Lidx_extra:
    ldr     r1, =KRExtraTable
    mov     r4, #0              @ pos
.Lidx_scan:
    ldrh    r2, [r1]
    cmp     r2, #0
    beq     .Lidx_none
    cmp     r2, r0
    beq     .Lidx_found
    add     r1, #2
    add     r4, #1
    b       .Lidx_scan
.Lidx_found:
    ldr     r0, =EXTRA_OFF
    add     r0, r0, r4
    pop     {r4, r5, pc}
.Lidx_none:
    mov     r0, #0
    sub     r0, #1              @ -1
    pop     {r4, r5, pc}

@ ------------------------------------------------------------
@ KR_GlyphBase: -> r0 = KRGlyphs_Dialog or KRGlyphs_Menu
@ (selects by active font's glyphs base == MENU_GLYPHS)
@ clobbers r1,r2
@ ------------------------------------------------------------
.thumb_func
KR_GlyphBase:
    ldr     r1, =gActiveFontPtr
    ldr     r1, [r1]            @ font
    ldr     r1, [r1, #4]        @ font->glyphs
    ldr     r2, =MENU_GLYPHS
    cmp     r1, r2
    beq     .Lgb_menu
    ldr     r0, =KRGlyphs_Dialog
    bx      lr
.Lgb_menu:
    ldr     r0, =KRGlyphs_Menu
    bx      lr

@ ------------------------------------------------------------
@ KR_GetGlyph: r0 = char* -> r0 = struct Glyph* (KR or ASCII
@ fallback, never NULL), r1 = byte length consumed.
@ ------------------------------------------------------------
.thumb_func
KR_GetGlyph:
    push    {r4, r5, r6, lr}
    mov     r4, r0              @ str
    bl      UTF8_Decode         @ r0=cp, r1=len
    mov     r5, r1              @ len
    mov     r6, r0              @ cp
    cmp     r1, #1
    beq     .Lgg_ascii          @ single byte -> vanilla path
    mov     r0, r6
    bl      KR_Index            @ r0 = idx or -1
    cmp     r0, #0
    blt     .Lgg_ascii_multi    @ multibyte but unmapped -> draw '?'
    @ glyph = base + idx*0x48
    mov     r1, #GLYPH_SIZE
    mul     r0, r1              @ r0 = idx*0x48
    mov     r4, r0
    bl      KR_GlyphBase        @ r0 = block base
    add     r0, r0, r4
    mov     r1, r5
    pop     {r4, r5, r6, pc}
.Lgg_ascii:
    @ single byte in r4[0]
    ldrb    r0, [r4]
    bl      KR_AsciiGlyph
    mov     r1, #1
    pop     {r4, r5, r6, pc}
.Lgg_ascii_multi:
    @ multibyte unknown -> '?' glyph, consume len bytes
    mov     r0, #0x3F
    bl      KR_AsciiGlyph
    mov     r1, r5
    pop     {r4, r5, r6, pc}

@ ------------------------------------------------------------
@ KR_AsciiGlyph: r0 = byte -> r0 = glyphs[byte] (or glyphs['?'])
@ ------------------------------------------------------------
.thumb_func
KR_AsciiGlyph:
    ldr     r1, =gActiveFontPtr
    ldr     r1, [r1]
    ldr     r1, [r1, #4]        @ glyphs base
    lsl     r2, r0, #2
    ldr     r0, [r1, r2]
    cmp     r0, #0
    bne     .Lag_ret
    mov     r2, #0x3F
    lsl     r2, r2, #2
    ldr     r0, [r1, r2]        @ glyphs['?']
.Lag_ret:
    bx      lr

@ ------------------------------------------------------------
@ char* KR_GetCharTextLen(char* str, u32* pWidth)   [0x3F3C]
@ ------------------------------------------------------------
.thumb_func
KR_GetCharTextLen:
    push    {r4, r5, lr}
    mov     r4, r0              @ str
    mov     r5, r1              @ pWidth
    bl      KR_GetGlyph         @ r0=glyph, r1=len
    ldrb    r2, [r0, #5]        @ width
    str     r2, [r5]
    add     r0, r4, r1          @ str + len
    pop     {r4, r5, pc}

@ ------------------------------------------------------------
@ int KR_GetStringTextLen(char* str)                [0x3EDC]
@ ------------------------------------------------------------
.thumb_func
KR_GetStringTextLen:
    push    {r4, r5, lr}
    mov     r4, r0              @ str
    mov     r5, #0              @ width
.Lgstl_loop:
    ldrb    r0, [r4]
    cmp     r0, #0
    beq     .Lgstl_end
    cmp     r0, #1              @ CHAR_NEWLINE
    beq     .Lgstl_end
    mov     r0, r4
    bl      KR_GetGlyph         @ r0=glyph, r1=len
    ldrb    r2, [r0, #5]
    add     r5, r5, r2
    add     r4, r4, r1
    b       .Lgstl_loop
.Lgstl_end:
    mov     r0, r5
    pop     {r4, r5, pc}

@ ------------------------------------------------------------
@ char* KR_DrawCharacter(struct Text* text, char* str)  [0x4180]
@ ------------------------------------------------------------
.thumb_func
KR_DrawCharacter:
    push    {r4, r5, r6, lr}
    mov     r4, r0              @ text
    mov     r5, r1              @ str
    mov     r0, r1
    bl      KR_GetGlyph         @ r0=glyph, r1=len
    mov     r6, r1              @ len
    @ font->drawGlyph(text, glyph)
    mov     r1, r0              @ glyph
    mov     r0, r4              @ text
    ldr     r2, =gActiveFontPtr
    ldr     r2, [r2]
    ldr     r3, [r2, #8]        @ drawGlyph
    bl      .Lcall_r3
    add     r0, r5, r6          @ str + len
    pop     {r4, r5, r6, pc}
.Lcall_r3:
    bx      r3

@ ------------------------------------------------------------
@ void KR_DrawString(struct Text* text, char* str)      [0x4004]
@ ------------------------------------------------------------
.thumb_func
KR_DrawString:
    push    {r4, r5, lr}
    mov     r4, r0              @ text
    mov     r5, r1              @ str
.Lds_loop:
    ldrb    r0, [r5]
    cmp     r0, #0
    beq     .Lds_end
    cmp     r0, #1
    beq     .Lds_end
    mov     r0, r4
    mov     r1, r5
    bl      KR_DrawCharacter    @ r0 = next str
    mov     r5, r0
    b       .Lds_loop
.Lds_end:
    pop     {r4, r5, pc}

.align 2
.pool
