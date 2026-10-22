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
git clone <이 레포 주소> maemul-check
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
tests/             test_engine.py (설계 3.4 더미 5건) · test_hub.py (fixture)
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
