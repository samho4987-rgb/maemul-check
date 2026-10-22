# 매물검수 (maemul-check)

광고에 적을 값과 건축물대장을 항목별로 대조해 누락·불일치를 게시 전에 잡아주는 무료 도구입니다.
공인중개사법 제18조의2 명시사항 위반을 올리기 전에 거릅니다.

> ※ 참고 자료이며 광고 등록 및 법적 판단 책임은 이용자에게 있습니다.

설계 전체는 [`매물검수_설계문서.md`](매물검수_설계문서.md)를 보세요.

## 준비물

- Python 3.11 이상
- 공공데이터포털(data.go.kr) 계정 + **건축HUB 건축물대장정보 서비스** 활용신청 → **Decoding 키**
  (Encoding 키를 쓰면 `SERVICE_KEY_IS_NOT_REGISTERED` 오류)

## 설치

```bash
git clone https://github.com/samho4987-rgb/maemul-check.git
cd maemul-check
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env      # 편집기로 열어 DATA_GO_KR_API_KEY= 뒤에 Decoding 키 붙여넣기
```

`.env` 는 `.gitignore` 에 들어 있어 커밋되지 않습니다. 키를 화면·채팅에 노출하지 마세요.

## 사용 (터미널)

```bash
# 대장 요약만
.venv/bin/python -m maemul_check "부산 수영구 광안동 170-5" --ho 301

# 광고 입력과 대조
.venv/bin/python -m maemul_check "부산 수영구 광안동 170-5" --ho 301 --ad examples/ad.json

# 여러 동 건물
.venv/bin/python -m maemul_check "부산 수영구 광안동 1" --dong 101 --ho 1203 --ad examples/ad.json

# JSON 출력
.venv/bin/python -m maemul_check "..." --ho 301 --ad examples/ad.json --json
```

`examples/ad.json` 을 복사해 자기 광고 값으로 바꿔 쓰면 됩니다. 필드는 설계 문서 6.1의 `ad` 형식과 같습니다.

판정: 초록(일치/기재) · 노랑(확인필요) · 빨강(불일치/누락) · 회색(조회불가)
종합: 빨강 1개 이상 → **수정 필요** / 노랑·회색만 → **확인 권장** / 전부 초록 → **게시 가능**

## 사용 (로컬 API 서버)

```bash
.venv/bin/pip install -e '.[server]'
.venv/bin/python -m server.app          # http://127.0.0.1:8000
curl localhost:8000/api/ping
curl -X POST localhost:8000/api/verify -H 'Content-Type: application/json' \
  -d '{"address":{"region":"부산 수영구 광안동","jibun":"170-5","dong":null,"ho":"301"},"ad":{...},"client_token":"아무-문자열"}'
```

| 응답 | 언제 |
|---|---|
| 200 | 검수 결과 + `quota` (대장이 없으면 `register_error:"register_not_found"`, 비교 항목은 조회불가) |
| 400 `bad_request` / `bad_address` | JSON·주소 형식 오류 |
| 422 `dong_required` / `ho_required` / `ho_not_found` | 동·호 선택 필요 (`candidates` 포함) |
| 429 `daily_limit` | 같은 `client_token` 이 하루(KST) 10건 초과 |
| 502 `register_unavailable` | 건축HUB 연결·키 오류 (`retry`) |

한도 차감은 200 일 때만. 환경변수는 `.env.example` 참고 (`QUOTA_LIMIT`, `QUOTA_DB`, `CORS_ORIGINS`).

## 테스트

```bash
.venv/bin/python -m pytest -v
```

실제 API를 호출하지 않습니다 (`tests/fixtures/` 응답 사용).

## 구조

```
maemul_check/
  schema.py        AdInput(14항목) · Report · ItemResult
  engine.py        verify(ad, register) -> Report   (순수 함수)
  compare/         항목별 비교 (면적·종류·층수·주차·날짜·소재지)
  rules/           required.json · purpose_map.json · tolerance.json
  pubdata/hub.py   건축HUB 2개 엔드포인트 → register dict (키는 인자로)
  pubdata/regions.py  주소 → 법정동코드
  cli.py           터미널 실행
server/
  app.py           Flask: POST /api/verify, GET /api/ping
  quota.py         일 한도 (SQLite, KST 자정 초기화)
  requirements.txt · render.yaml
tests/             test_engine.py (설계 3.4 더미 5건 + 고시 룰) · test_hub.py (fixture) · test_server.py
```

## 출처·라이선스

- 코드: MIT
- `maemul_check/pubdata/resources/region_codes.txt`: 행정안전부 법정동코드 전체자료 중 현존 행.
  [coding-realtor/building-register-mcp](https://github.com/coding-realtor/building-register-mcp) (Apache-2.0) 에 포함된 파일을 가져와 폐지 행을 뺐습니다. 지역코드 검색·API 파싱 로직도 이 레포를 참고했습니다.

---

## 세션 핸드오프

### 세션 1 (2026-10-22) — 패키지 + CLI

**완료**
- `maemul_check/` 패키지 (설계 5절 구조): schema · engine · compare 6종 · rules 3종 · pubdata(hub, regions) · cli
- 테스트 19건 통과 (설계 3.4 더미 5건 포함, 실제 API 호출 없음)
- `python -m maemul_check "주소" --ho 301 [--ad 파일]` 동작

**설계 대비 결정사항**
- register dict 에 소재지 비교용 키 3개 추가: `대지위치`(platPlc) `동명칭` `호명칭`
- 주차: 광고 = 대장 → 일치, 광고 < 대장 → 확인필요, 광고 > 대장 → 불일치 (설계의 "≤ → 확인필요"에서 같을 때만 일치로)
- 종합 판정에서 회색(조회불가)은 노랑과 같이 "확인 권장"으로 처리
- 종류: 단일 용도가 허용 목록이면 일치, 복수 용도 중 일부만 허용이면 확인필요, 원룸은 항상 확인필요
- 대장 조회 실패 시 비교 7항목은 조회불가, 누락 체크 7항목은 그대로 판정
- 실행 편의용 `maemul_check/__main__.py`, `examples/ad.json` 추가 (5절 구조 외)

**막힌 부분 / 다음**
- 고시 최신 원문 대조 미완: law.go.kr·molit.go.kr 본문이 자동으로 안 읽힘. 2024-10 개정 예고(국토부 고시 제2024-1393호)까지만 확인 → **사람이 law.go.kr 에서 「중개대상물의 표시·광고 명시사항 세부기준」 현행본을 열어 3.1 표·관리비 10만원 기준과 대조 필요**
- 다음 세션 2: `server/` Flask API (`POST /api/verify`, `GET /api/ping`) + 일 10건 한도. `hub.HubError.code` 를 응답 `error` 로 그대로 쓰면 됨

### 세션 2 ① (2026-10-23) — 고시 제2024-748호 반영

**완료**
- `AdInput` 필드 3개 추가: `floor`(해당층 — 3 / "지하1" / "B1" / "저"·"중"·"고") · `direction_basis`("주실"·"거실"·"안방" / "주출입구") · `parking_unit`("총" / "세대당")
- 소재지: 지번 일치 + 집합건물은 동·해당층 일치. **호는 더 이상 비교 안 함**(명시사항 아님). 저/중/고 → 확인필요. 여러 문제가 겹치면 누락 > 불일치 > 확인필요 > 조회불가 순으로 대표 판정, 비고에는 전부 표시
- 주차: 단위 미기재 → 누락. 세대당은 `총주차 ÷ 세대수`(소수 1자리)와 비교
- 방향: 8방위 + 기준 둘 다 있어야 기재
- 관리비: 종류가 상가/점포·사무실이면 미기재도 기재 처리. 10만원 이상 → 확인필요(비목별 금액)
- 입주가능일: "협의" 제거, "○월 초순/중순/하순" 허용
- register dict 에 `해당층` 추가 (전유 행 `flrNo`, `flrGbCdNm`=지하면 음수)
- 테스트 19 → 67건 통과

**설계 대비 결정사항**
- 일반건물(단독·다가구 등)은 해당층을 요구·비교하지 않음 (대장에 호별 층이 없음, 단독주택은 고시상 지번만)
- 세대당 주차: 세대수가 0/없으면(오피스텔 등) `호수`로 나눔 → 비고에 어느 쪽으로 나눴는지 표시
- 집합건물에서 대장에 동명칭이 있는데 광고에 동이 없으면 누락
- 방향 기준이 종류와 맞는지(주거=주실, 비주거=주출입구)는 아직 안 봄

**다음**
- 세션 2 ②: `server/` Flask API (`POST /api/verify`, `GET /api/ping`) + 일 10건 한도. `hub.HubError.code` 를 응답 `error` 로 그대로 쓰면 됨. 요청 `ad` 에 위 3필드 포함(설계 6.1 예시 갱신됨)

### 세션 2 ② (2026-10-23) — server/ Flask API

**완료**
- `server/app.py` (`create_app()` 팩토리 + 모듈 수준 `app`), `server/quota.py`, `requirements.txt`, `render.yaml`
- 로컬 curl 3종 확인: 200(실제 건축HUB 1회 호출) · 429(`QUOTA_LIMIT=1` 로 2번째 요청) · 502(`HTTPS_PROXY` 를 죽은 포트로 → 연결 실패, `retry:true`). 로그·응답에 키 노출 없음
- 테스트 67 → 78건 통과 (`tests/test_server.py`, fixture 사용)

**설계 대비 결정사항**
- 상태코드 추가: 400(입력 오류), 422(동·호 선택 필요, `candidates`). 6.1 에는 200/429/502 만 있음
- `register_not_found`(신축·멸실)는 502 가 아니라 **200 + 비교 항목 조회불가** (설계 3.2 "누락은 대장 없이도 잡힌다"). 응답에 `register_error` 필드 추가
- 한도는 200 응답에서만 차감. 키는 `client_token`, 없으면 IP(`X-Forwarded-For` 첫 값)
- 로컬 기본 포트 8000 (macOS 는 5000 을 AirPlay 가 씀)
- `CORS_ORIGINS` 비우면 전부 허용(로컬용) → Render 에서는 반드시 Pages 주소로 설정

**현재 (세션 2 종료 시점)**
- 엔진: 고시 제2024-748호 기준 14항목 룰 반영, `AdInput` 에 `floor` `direction_basis` `parking_unit`
- 실행 경로 2개: 터미널 `python -m maemul_check ...` / 로컬 API `python -m server.app` (8000)
- 테스트 78건 전부 통과, 실API 호출 없음. 배포·웹 화면은 아직 없음

**막힌 부분 / 다음**
- `client_token` 은 브라우저가 만드는 값이라 바꾸면 한도 우회 가능. 필요해지면 IP 한도를 겹쳐 걸 것
- 설계 6절 1단계의 `/api/building?region&jibun`(동 목록 조회)은 6.1 명세에 없어 미구현 → 세션 3 에서 필요하면 추가. 지금은 422 `candidates` 로 동 목록을 받을 수 있음
- Render 는 기본적으로 레포 루트의 `render.yaml` 을 찾음 → 세션 3 에서 Blueprint 경로를 `server/render.yaml` 로 지정하거나 루트로 옮길 것
- 다음 세션 3: `web/index.html` + GitHub Pages + Render 배포
