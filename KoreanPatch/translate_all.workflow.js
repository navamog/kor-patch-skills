export const meta = {
  name: 'tmgc-translate-all',
  description: 'Translate all remaining TMGC text files (story/characters/endings) to Korean using the fixed glossary',
  phases: [{ title: 'Translate', detail: 'one subagent per text file, edits in place' }],
}

// args = JSON array of file paths relative to the Text/ directory
const TEXTDIR = 'D:\\Works\\FEm\\TMGC_Buildfiles\\Text\\'
const GLOSSARY = 'D:\\Works\\FEm\\TMGC_Buildfiles\\KoreanPatch\\glossary.tsv'
let files = []
if (Array.isArray(args)) files = args
else if (typeof args === 'string') { try { files = JSON.parse(args) } catch (e) { files = [] } }

function prompt(rel) {
  const abs = TEXTDIR + rel.replace(/\//g, '\\')
  return `Fire Emblem 팬게임 "The Morrow's Golden Country" 한글패치. 아래 파일의 영어를 자연스러운 한국어로 번역하고 **파일을 직접 수정(Edit/Write)**하라.

## 대상 파일
${abs}

## 1단계: 반드시 먼저 용어집을 읽어라
${GLOSSARY} 파일을 Read하여 인명·지명 한글 표기를 확인하고 **그대로 통일 사용**하라. 용어집에 없는 고유명사는 국립국어원 외래어표기법 기준으로 음역하되, 같은 파일 내에서 일관되게.

## 절대 규칙 (위반 시 빌드 실패 — ParseFile + 태그 검증기가 잡아냄)
0. **엔트리를 하나도 잃어버리지 마라.** 파일의 모든 엔트리를 빠짐없이 번역해 남긴다.
   - 시작 전: \`grep -c "^##" <파일>\` (또는 \`^# 0x\`)로 **원본 엔트리 개수를 세어 기록**하라.
   - 큰 파일은 Write로 통째 재작성하지 말고 **Edit로 구간을 나눠 순차 수정**하라. 통짜 재작성은 뒷부분 누락 사고의 원인이다.
   - 끝난 뒤: 같은 명령으로 **개수가 원본과 정확히 같은지 반드시 확인**하고, 다르면 누락분을 복구하라.
   - 엔트리 순서도 원본 그대로 유지한다.
1. \`#\` 또는 \`##\`로 시작하는 줄(엔트리 ID/태그)은 **한 글자도 바꾸지 마라**. 뒤의 \`^\`/\`*\` 마커와 후행 공백까지 원본 그대로. 이 태그는 다른 소스가 참조하는 식별자다.
2. 대괄호 코드 \`[X] [N] [NL] [A] [.] [0x##]\` 및 모든 \`[코드]\`(예: [OpenRight] [LoadFace] [Blair] [ToggleMouthMove] [OpenQuote] [CloseQuote] [SwordIcon] 등 화자·연출·아이콘 코드)는 **절대 번역/삭제/이동/추가하지 말고 원위치 그대로** 둔다. 각 텍스트 끝 \`[X]\`, 줄바꿈 \`[N]\`/\`[NL]\` 필수 유지.
2b. **\`[...]\` (말줄임 연출)은 실제로 가장 자주 누락되는 코드다.** 원문 한 줄에 \`[...]\`가 2개면 번역문에도 2개여야 한다.
   한국어 어순 때문에 위치는 옮겨도 되지만 **개수는 절대 줄이지 마라**. \`[.]\`도 마찬가지.
3. 대사창 폭을 넘지 않게 각 \`[N]\` 줄을 원문과 비슷한 길이로. 한국어가 더 짧으니 대개 여유 있음. 문단 구분 \`[N][N]\`/\`[A]\` 위치 보존.
4. 영어 산문만 번역. 숫자·퍼센트·수식·좌표·고유 코드값은 유지.
5. **의도적으로 깨진 문자열/개그 코드값**(hex 나열, ??? , Beep/Boop, 대명사 표기줄 등)은 원문 유지.

## 능력치/공통 용어 (통일)
HP=체력, Str=힘, Mag=마력, Skill=기술, Speed=속도, Luck=행운, Def=수비, Res=마방, Move=이동, Con=체격, Level=레벨, EXP=경험치, Attack=공격, Hit=명중, Crit=필살, Avoid=회피, Range=사거리, unit=유닛, turn=턴, army=군대, kingdom=왕국, empire=제국, knight=기사, lord=경/영주(문맥), Sir=경, Lady=님/영애, Your Majesty=폐하, Your Highness=전하, General=장군.

## 문체
- 대사는 캐릭터 성격에 맞는 자연스러운 한국어 구어체. 반말/존댓말은 관계에 맞게.
- 나레이션·설명은 문어체.
- 어색한 직역 금지. 한국어로 읽어서 자연스럽게.

## 완료 후 (필수 자체검증)
Bash로 원본 대비 개수를 실제로 확인하라:
\`git show HEAD:"TMGC_Buildfiles/Text/${rel}" | grep -c "^##"\` 와 현재 파일의 \`grep -c "^##"\` 가 **일치해야 한다**
(숫자 ID 파일이면 \`^# 0x\` 기준).
또한 **대괄호 코드 전체의 개수(multiset)를 원본과 대조**하라 — \`[X]\`뿐 아니라 \`[N]\` \`[A]\` \`[...]\` \`[.]\` 전부.
python으로 \`re.findall(r'\\[[^\\]\\n]*\\]', text)\`를 원본/현재에 돌려 \`collections.Counter\`를 비교하는 게 확실하다.
(순서는 어순 때문에 달라질 수 있으니 **개수만** 맞으면 된다.) 불일치하면 반드시 고친 뒤 끝내라.
그리고 **결과를 한 줄로** 반환하라(예: "Prologue.txt: 42 entries, tags 42/42 OK").`
}

log(`translating ${files.length} files`)
const results = await parallel(
  files.map((f) => () =>
    agent(prompt(f), { label: 'tr:' + f, phase: 'Translate' }).then(
      (r) => ({ file: f, ok: true, note: (r || '').slice(0, 120) }),
      (e) => ({ file: f, ok: false, note: String(e).slice(0, 120) })
    )
  )
)
const failed = results.filter((r) => r && !r.ok)
log(`done: ${results.length} files, ${failed.length} failed`)
return { total: results.length, failed: failed.map((f) => f.file), results }
