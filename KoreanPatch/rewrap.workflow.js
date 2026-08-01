export const meta = {
  name: 'tmgc-rewrap-overwide',
  description: 'Tighten Korean dialogue lines that exceed the FE8 text box width',
  phases: [{ title: 'Rewrap', detail: 'one subagent per file, edits in place' }],
}

// args = ["Chapter Text/Interlude10.txt", ...]  (paths relative to Text/)
const TEXTDIR = 'D:\\Works\\FEm\\TMGC_Buildfiles\\Text\\'
const BUDGET = 205 // px, safety margin under the measured 213px budget

let groups = []
if (Array.isArray(args)) groups = args
else if (typeof args === 'string') { try { groups = JSON.parse(args) } catch (e) { groups = [] } }

function prompt(rel) {
  const abs = TEXTDIR + rel.replace(/\//g, '\\')
  const list = `아래 명령으로 **네가 고쳐야 할 줄 목록**을 먼저 뽑아라(줄번호·현재폭·내용):
\`\`\`
cd /d/Works/FEm && python -c "
import json,io
d=json.load(io.open('TMGC_Buildfiles/KoreanPatch/_overwide_lines.json',encoding='utf-8'))
for x in d['lines']:
    if x['file']=='${rel}': print(x['line'], x['width'], x['text'])
"
\`\`\``
  return `Fire Emblem 팬게임 "The Morrow's Golden Country" 한글패치 — **대사 줄 폭 초과 수정**.

## 왜 고쳐야 하나
FE8은 \`[N]\`으로 끊긴 줄을 **고정 폭 버퍼**에 그리고 자동 줄바꿈을 하지 않는다.
폭을 넘긴 줄은 **화면에 아예 안 나오거나(빈 대사창)** 중간부터 글자가 깨진다. 실제로 게임에서 확인된 버그다.

## 대상 파일
${abs}

## 고쳐야 할 줄
${list}

## 목표
각 줄의 렌더링 폭을 **${BUDGET}px 이하**로 줄인다. 한글 1글자 = 12px, 공백 = 약 3px, 대괄호 코드는 0px(안 그려짐).
→ 대략 **한글 16글자 + 공백 몇 개**가 상한이다. 넉넉히 15글자 이하로 맞추면 안전하다.

## 방법: 문장을 짧게 다듬어라
- \`[N]\`의 개수와 위치를 바꾸지 마라. 줄 사이로 단어를 옮기면 다음 줄이 넘쳐서 문제가 번진다.
- **같은 줄 안에서** 표현을 압축한다. 예:
  - "이 거래를 받아들이고 우리에게 협조한다면," → "이 거래를 받아들여 협조한다면,"
  - "자네를 위해 조촐한 제안서를 하나 써 두었네." → "자네에게 줄 제안서를 써 두었네."
- 군더더기 부사·중복 표현·장황한 연결어미를 덜어낸다. **의미와 말투는 유지**한다.
- 존댓말/반말, 캐릭터 말투, 고유명사 표기는 절대 바꾸지 마라.

## 절대 규칙 (위반 시 빌드 실패)
1. \`#\`/\`##\`로 시작하는 줄은 한 글자도 건드리지 마라.
2. 대괄호 코드(\`[N]\` \`[A]\` \`[X]\` \`[...]\` \`[.]\` \`[OpenLeft]\` \`[LoadFace]\` 등)는 **개수·순서·위치 모두 원본 그대로**. 지우거나 옮기거나 추가 금지.
3. 지정된 줄만 수정한다. 다른 줄은 손대지 마라.
4. 엔트리 개수·순서 불변.

## 완료 후 자체검증 (필수)
아래를 Bash로 실행해 **0개**가 나오는지 확인하라. 남아 있으면 더 줄여라.
\`\`\`
cd /d/Works/FEm && cd /d/Works/FEm && python TMGC_Buildfiles/KoreanPatch/check_line_width.py >/dev/null 2>&1 && python -c "
import json,io
d=json.load(io.open('TMGC_Buildfiles/KoreanPatch/_overwide_lines.json',encoding='utf-8'))
n=[x for x in d['lines'] if x['file']=='${rel}']
print('REMAINING', len(n))
for x in n: print(' ', x['line'], x['width'], x['text'][:50])
"
\`\`\`
그리고 대괄호 코드 보존을 확인하라:
\`\`\`
cd /d/Works/FEm && python TMGC_Buildfiles/KoreanPatch/verify_entries.py 2>&1 | head -5
\`\`\`
\`DAMAGED: 0\` 이어야 한다.

결과를 한 줄로 반환하라 (예: "Prologue.txt: 12 lines rewrapped, all <=${BUDGET}px, codes intact").`
}

log(`rewrapping ${groups.length} files`)
const results = await parallel(
  groups.map((g) => () =>
    agent(prompt(g), { label: 'rw:' + g, phase: 'Rewrap' }).then(
      (r) => ({ file: g, ok: true, note: (r || '').slice(0, 140) }),
      (e) => ({ file: g, ok: false, note: String(e).slice(0, 140) })
    )
  )
)
const failed = results.filter((r) => r && !r.ok)
log(`done: ${results.length} files, ${failed.length} failed`)
return { total: results.length, failed: failed.map((f) => f.file), results }
