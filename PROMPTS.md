# 프롬프트 모음

> 모든 프롬프트는 `매물검수_설계문서.md`가 같은 폴더에 있다는 전제.
> Claude Code 실행(`claude`) → `/model opus` → 아래 중 한 가지 방법으로.

## 쓰는 법 — 복사할 필요 없음

**방법 1 (권장)**: Claude Code에 이 파일을 읽게 한다. 제목만 부르면 된다.
```
PROMPTS.md 열어서 1편 "시작" 프롬프트대로 해
```
다음 단계도 같은 식: `PROMPTS.md 1편 "실주소 1회" 해`, `PROMPTS.md 2편 "시작 ② API 서버" 해`

**방법 2**: GitHub에서 이 파일을 열면 각 회색 상자 오른쪽 위에 복사 아이콘이 있다. 클릭 → Claude Code에 붙여넣기.

---

---

## 1편 — 검수 엔진

**시작**
```
매물검수_설계문서.md 읽고 8절 세션 1 진행. 5절 구조대로 패키지 생성, 3.4 테스트 5건 통과가 완료 조건. 실제 API 호출은 cli 1회만.
```

**계획을 말하면**
```
진행해
```

**테스트 실행**
```
pytest 돌려
```

**테스트 실패 시**
```
실패 원인 한 줄로 말하고 고쳐
```

**.env 만들기** (키는 Claude Code 채팅에 절대 붙여넣지 않는다 — 대화 기록에 남는다)
```
.env.example을 복사해서 .env 만들어. 키는 내가 직접 넣을게. .env가 .gitignore에 있는지도 확인해.
```
→ 생성되면 **에디터로 `.env`를 열어** `DATA_GO_KR_API_KEY=` 뒤에 키를 붙여넣고 저장.
- Mac: VS Code 탐색기에서 `.env` 클릭
- Windows(VS Code 없을 때): 명령창에서 `notepad .env`
- 키는 data.go.kr 마이페이지 → 인증키 → **Decoding** 키

**실주소 1회**
```
.env의 키로 python -m maemul_check "자기 사무실 주소" 실행하고 결과 보여줘
```
→ 주소는 지번 주소("부산 수영구 광안동 170-5" 형식). 집합건물이면 `--ho 301` 추가.

**핸드오프**
```
핸드오프 요약 써줘. 완료/현재/다음/막힌 부분. README 하단에 추가해.
```

**커밋**
```
전부 커밋해. 메시지는 "세션 1: 패키지·테스트·CLI"
```

### 상황별 (필요할 때만)

| 상황 | 프롬프트 |
|---|---|
| 폴더 구조가 문서와 다름 | `5절 구조랑 다르다. 문서대로 맞춰` |
| 테스트에서 실제 API를 호출하려 함 | `테스트는 fixture로. 실호출은 cli 마지막 1회만` |
| API 키를 코드에 넣으려 함 | `키는 인자로. 환경변수 읽기는 cli에서만` |
| 설계를 바꾸자고 함 | `멈춰. 설계 문서대로 가고, 바꿀 건 핸드오프에 적어` |

---

## 2편 — API 서버

**세션 시작 전**: Claude Code에 `/clear` (1편 대화를 비운다. 맥락은 README 핸드오프에 있다)

**시작 ① 룰셋 갱신** (고시 대조 결과 반영)
```
매물검수_설계문서.md 읽고 8절 세션 2의 ① 진행. README 하단 핸드오프부터 읽어. 3.1 표가 고시 제2024-748호 기준으로 바뀌었으니 소재지·주차·방향·관리비 룰과 AdInput 필드(floor, direction_basis, parking_unit)를 맞추고 테스트 추가. pytest 전부 통과가 완료 조건.
```

**README 정리** (①이 끝난 뒤)
```
README의 git clone 주소를 실제 레포 주소로 바꿔
```

**시작 ② API 서버**
```
8절 세션 2의 ② 진행. 6.1 API 명세대로 server/ 구현, curl로 200/429/502 세 응답 확인이 완료 조건.
```

**curl 확인** (Claude가 안 보여주면)
```
서버 띄우고 curl로 200, 429, 502 순서대로 보여줘. 429는 11번째 호출, 502는 잘못된 키로.
```

**핸드오프**
```
핸드오프 요약 써줘. 완료/현재/다음/막힌 부분. README 하단에 추가해.
```

**커밋·push**
```
전부 커밋하고 push해. 메시지는 "세션 2: 룰셋 갱신·API 서버"
```

### 상황별 (필요할 때만)

| 상황 | 프롬프트 |
|---|---|
| Flask 말고 다른 걸 쓰려 함 | `설계 7절대로 Flask` |
| 키를 코드에 넣으려 함 | `키는 환경변수. server/app.py에서만 읽어` |
| 한도 저장을 복잡하게 만듦 | `5.4대로 SQLite 한 테이블. 소실 허용` |

---

## 3편 — 웹 화면 + 배포

**GitHub에 올리기** (0편에서 `gh` CLI 설치·로그인이 돼 있어야 한다)
```
GitHub에 내 계정으로 maemul-check 공개 레포를 만들고 origin으로 연결해서 main 브랜치 push해. 공개 레포니까 .env가 안 올라가는지 먼저 확인해.
```

**세션 시작 전**: `/clear`

**① 화면 만들기**
```
매물검수_설계문서.md 읽고 8절 세션 3 진행. README 하단 핸드오프부터 읽어. 6절 3단계 화면을 docs/index.html 단일 파일로, docs/prompts.html(PROMPTS.md를 복사 버튼 페이지로), docs/config.js(API_BASE·KAKAO_JS_KEY 자리). render.yaml은 레포 루트로 이동. 로컬 서버(8000)로 검수 1건 동작 확인이 완료 조건. 배포는 내가 브라우저에서 한다.
```

**② 커밋·push** (배포 전에 코드가 GitHub에 있어야 한다)
```
전부 커밋하고 push해. 메시지는 "세션 3: 웹 화면"
```

**③ Render 배포** — 브라우저에서 (Claude Code 아님)
1. render.com → Dashboard → **New → Blueprint** → `maemul-check` 레포 선택 → Apply
2. 생성된 서비스 → **Environment** → 추가: `DATA_GO_KR_API_KEY` = (자기 키), `CORS_ORIGINS` = `https://<GitHub계정>.github.io`
3. 배포 끝나면 서비스 주소 복사 (예: `https://maemul-check-api.onrender.com`) → 브라우저에서 `/api/ping` 열어 응답 확인

**④ 설정값 넣기**
```
docs/config.js에 API_BASE를 (Render 주소)로, KAKAO_JS_KEY를 (카카오 JS 키)로 넣고 커밋·push해
```

**⑤ GitHub Pages 켜기** — 브라우저에서
1. GitHub 레포 → **Settings → Pages** → Source: Deploy from a branch → Branch `main`, Folder **`/docs`** → Save
2. 1~2분 뒤 `https://<GitHub계정>.github.io/maemul-check/` 열림

**⑥ 카카오 도메인 등록** — 브라우저에서
developers.kakao.com → 내 앱 → **플랫폼 → Web → 사이트 도메인**에 `https://<GitHub계정>.github.io` 추가

**⑦ 실제 검수 1건**
```
배포 주소는 https://<GitHub계정>.github.io/maemul-check/ 야. 열어서 내 사무실 주소로 검수 1건 돌리고 결과 확인해. 안 되면 원인을 CORS / 카카오 도메인 / Render 환경변수 중 어디인지 짚어줘.
```

**핸드오프·커밋**
```
핸드오프 요약 써줘. 완료/현재/다음/막힌 부분. README 하단에 추가하고, README 맨 위에 배포 주소를 넣어. 전부 커밋하고 push. 메시지는 "세션 3: 배포 완료"
```

### 상황별

| 상황 | 프롬프트 |
|---|---|
| React 등 프레임워크를 쓰려 함 | `설계 5절대로 단일 HTML. 빌드 없음` |
| Render가 render.yaml을 못 찾음 | 루트에 있는지 확인: `render.yaml이 레포 루트에 있는지 확인하고 없으면 옮겨서 push` |
| 화면에서 API 호출이 막힘(CORS) | Render Environment의 `CORS_ORIGINS` 값이 Pages 주소와 정확히 같은지(끝에 `/` 없음) |
| 카카오 주소검색이 안 뜸 | 카카오 플랫폼 도메인에 `https://<계정>.github.io` 등록됐는지 |
| 첫 호출이 50초 걸림 | 정상. Render 무료 플랜 콜드스타트. 화면에 안내 문구가 떠야 함 |

---

## 공통

| 상황 | 프롬프트 |
|---|---|
| 뭘 하는지 모르겠을 때 | `지금 뭐 하는 중인지 한 줄로` |
| 너무 많이 바꿀 때 | `한 번에 하나씩. 지금 건 뭐야` |
| 에러가 반복될 때 | `같은 에러 3번째. 접근을 바꿔서 설명부터 해` |
| 끝내고 싶을 때 | `여기까지 커밋하고 핸드오프 요약` |
