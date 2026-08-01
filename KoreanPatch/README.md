# TMGC 한글패치 — 엔진/폰트 모듈

Fire Emblem: The Morrow's Golden Country (FE8U buildfiles 핵)의 UTF-8 한글화 엔진.

## 구성
- `gen_font.py` — Windows TTF(gulim.ttc)를 16×16 2bpp FE8 Glyph 레코드로 변환. 대사(12px)/메뉴(11px) 2세트. 음절(U+AC00–D7A3 11172자)+호환자모+extras를 연속 블록으로 생성 → `kr_dialog.dmp`/`kr_menu.dmp`.
- `KRTextEngine.s` — Thumb 어셈블리 UTF-8 텍스트 엔진. 코드포인트를 산술로 글리프 주소 계산(base+idx*0x48). ASCII/narrow는 바닐라 `glyphs[]` 폴백.
- `KRFontData.event` — gen_font.py 생성물(글리프 블록 + KRExtraTable 심볼).
- `KRTextEngine.lyn.event` — `as`→`lyn` 산출 EA 이벤트.
- `KoreanInstaller.event` — 글리프+엔진 배치 및 4개 함수 트램폴린 훅.
- `text-process-kr.py` — text-process-classic + 비ASCII→`[0xNN]` UTF-8 이스케이프(ParseFile 대응).
- `c2ea.py`/`nightmare.py` — 인코딩 패치(latin-1)한 NMM2CSV.

## 훅 대상 (FE8U)
| 주소 | 함수 |
|---|---|
| 0x3EDC | GetStringTextLen |
| 0x3F3C | GetCharTextLen |
| 0x4004 | Text_DrawString |
| 0x4180 | Text_DrawCharacter |

## 재빌드
1. 클린 FE8U 롬을 `../FE8_clean.gba`로 저장 (SHA1 `c25b145e37456171ada4b0d440bf88a19f4d509f`).
2. 엔진 asm 수정 시: `arm-none-eabi-as -mthumb -mcpu=arm7tdmi KRTextEngine.s -o KRTextEngine.o && lyn KRTextEngine.o > KRTextEngine.lyn.event`
3. `..\MAKE_KR.cmd` 실행 → `TMGC.gba` + `TMGC-KR.ups`.

## 주의
- ColorzCore nested `#include`는 **포함 파일 기준 상대경로**.
- Mesen 등 일부 에뮬은 32MB 패딩 필요(`TMGC_padded.gba`).
- 폰트: 8방향 아웃라인 헤일로 방식(값 2=ink, 3=outline). 품질 개선 시 gen_font.py의 render_char 임계값 조정.
