"""건축HUB 건축물대장 API 2개 엔드포인트 → register dict (설계 4절).

키는 인자로 받는다. 환경변수는 cli.py·server/app.py 에서만 읽는다.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

import requests

BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"
TIMEOUT = 10
RETRIES = 2
PAGE_SIZE = 100
MAX_PAGES = 20   # 전유공용면적 클라이언트 필터 폴백 상한 (2,000행)

HttpGet = Callable[..., Any]   # requests.get 과 같은 시그니처


# ── 오류 ────────────────────────────────────────────────────────

class HubError(Exception):
    """대장 조회 실패. code 는 server 에서 응답 코드로 쓴다."""
    code = "register_unavailable"

    def __init__(self, message: str, *, retry: bool = False, candidates: list[str] | None = None):
        super().__init__(message)
        self.retry = retry
        self.candidates = candidates or []


class RegisterNotFound(HubError):
    code = "register_not_found"


class DongRequired(HubError):
    code = "dong_required"


class HoRequired(HubError):
    code = "ho_required"


class HoNotFound(HubError):
    code = "ho_not_found"


# ── HTTP ───────────────────────────────────────────────────────

def _parse(text: str) -> tuple[list[dict], int]:
    try:
        data = json.loads(text)
    except ValueError:
        # 키 오류 등은 JSON 이 아니라 XML 로 온다
        m = re.search(r"<returnAuthMsg>(.*?)</returnAuthMsg>", text) or re.search(r"<resultMsg>(.*?)</resultMsg>", text)
        msg = m.group(1) if m else "알 수 없는 응답"
        hint = " (Decoding 키를 쓰세요)" if "SERVICE_KEY" in msg else ""
        raise HubError(f"건축HUB 오류: {msg}{hint}") from None

    response = data.get("response", {})
    header = response.get("header", {})
    if str(header.get("resultCode", "00")) not in ("00", "0", "000"):
        raise HubError(f"건축HUB 오류: {header.get('resultCode')} {header.get('resultMsg', '')}".strip())

    body = response.get("body", {}) or {}
    items = body.get("items")
    items = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(items, dict):
        items = [items]
    return items, int(body.get("totalCount") or 0)


def _call(api_key: str, endpoint: str, params: dict, http_get: HttpGet) -> tuple[list[dict], int]:
    query = {"serviceKey": api_key, "_type": "json", **{k: v for k, v in params.items() if v not in (None, "")}}
    last = ""
    for _ in range(1 + RETRIES):
        try:
            resp = http_get(f"{BASE_URL}/{endpoint}", params=query, timeout=TIMEOUT)
            resp.raise_for_status()
            return _parse(resp.text)
        except requests.HTTPError as e:
            last = f"HTTP {e.response.status_code if e.response is not None else '?'}"
        except requests.RequestException as e:
            # 예외 문자열에는 serviceKey 가 든 URL 이 섞일 수 있어 타입명만 남긴다
            last = type(e).__name__
    raise HubError(f"건축HUB 연결 실패 ({endpoint}: {last})", retry=True)


# ── 값 변환 ─────────────────────────────────────────────────────

def _str(v: Any) -> str | None:
    s = str(v).strip() if v is not None else ""
    return s or None


def _int(v: Any) -> int | None:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _float(v: Any) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _date(v: Any) -> str | None:
    s = re.sub(r"\D", "", str(v or ""))
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else None


def _floor(item: dict) -> int | None:
    """전유부 flrNo → 지하는 음수."""
    n = _int(item.get("flrNo"))
    if n is not None and n > 0 and "지하" in (_str(item.get("flrGbCdNm")) or ""):
        return -n
    return n


def _purpose(item: dict) -> str | None:
    """용도는 etcPurps 우선, 없으면 mainPurpsCdNm."""
    return _str(item.get("etcPurps")) or _str(item.get("mainPurpsCdNm"))


def _norm_dong(v: Any) -> str:
    return (_str(v) or "").removesuffix("동")


def _norm_ho(v: Any) -> str:
    return (_str(v) or "").removesuffix("호").lstrip("0")


# ── 표제부 선택 ─────────────────────────────────────────────────

def select_title(titles: list[dict], dong: str | None = None) -> tuple[dict, str]:
    """주건축물 우선. 여러 동이면 dong 필수. → (표제부, 비고)"""
    main = [t for t in titles if _str(t.get("mainAtchGbCdNm")) == "주건축물"] or titles
    names = sorted({_str(t.get("dongNm")) or "" for t in main} - {""})

    if dong:
        picked = [t for t in main if _norm_dong(t.get("dongNm")) == _norm_dong(dong)]
        if not picked:
            raise DongRequired(f"'{dong}' 동이 대장에 없음", candidates=names)
        main = picked
    elif len(main) > 1 and len(names) > 1:
        raise DongRequired(f"동이 {len(names)}개인 건물 → 동 선택 필요", candidates=names)

    note = f"표제부 {len(titles)}건 중 주건축물 선택" if len(titles) > 1 else ""
    return main[0], note


# ── 전유공용면적 ────────────────────────────────────────────────

def _match_unit(item: dict, dong: str | None, ho: str) -> bool:
    if _norm_ho(item.get("hoNm")) != _norm_ho(ho):
        return False
    return not dong or _norm_dong(item.get("dongNm")) == _norm_dong(dong)


def _fetch_unit(api_key: str, base: dict, dong: str | None, ho: str, http_get: HttpGet) -> tuple[list[dict], int]:
    """→ (해당 호 행들, 건물 전체 전유공용 행 수). 서버 필터 실패 시 전체를 받아 걸러낸다."""
    params = {**base, "dongNm": dong, "hoNm": _norm_ho(ho), "numOfRows": PAGE_SIZE, "pageNo": 1}
    items, _ = _call(api_key, "getBrExposPubuseAreaInfo", params, http_get)
    rows = [i for i in items if _match_unit(i, dong, ho)]
    if rows:
        return rows, len(items)

    total, page = 0, 1
    while page <= MAX_PAGES:
        items, total = _call(api_key, "getBrExposPubuseAreaInfo", {**base, "numOfRows": PAGE_SIZE, "pageNo": page}, http_get)
        rows += [i for i in items if _match_unit(i, dong, ho)]
        if not items or page * PAGE_SIZE >= total:
            break
        page += 1
    return rows, total


# ── register dict ───────────────────────────────────────────────

def build_register(title: dict, unit_rows: list[dict] | None = None, note: str = "") -> dict[str, Any]:
    """표제부 1건 + 해당 호 전유공용면적 행들 → register dict (설계 4절 계약)."""
    unit_rows = unit_rows or []
    excl = [r for r in unit_rows if "전유" in (_str(r.get("exposPubuseGbCdNm")) or "")]
    comm = [r for r in unit_rows if "공용" in (_str(r.get("exposPubuseGbCdNm")) or "")]
    excl_area = round(sum(_float(r.get("area")) or 0 for r in excl), 4) if excl else None
    comm_area = sum(_float(r.get("area")) or 0 for r in comm)

    parking = [_int(title.get(k)) for k in ("indrMechUtcnt", "oudrMechUtcnt", "indrAutoUtcnt", "oudrAutoUtcnt")]
    unit = excl[0] if excl else (unit_rows[0] if unit_rows else {})

    return {
        "건물명": _str(title.get("bldNm")),
        "용도": _purpose(title),
        "호_용도": _purpose(unit) if unit else None,
        "구조": _str(title.get("strctCdNm")),
        "지상층수": _int(title.get("grndFlrCnt")),
        "지하층수": _int(title.get("ugrndFlrCnt")),
        "세대수": _int(title.get("hhldCnt")),
        "가구수": _int(title.get("fmlyCnt")),
        "호수": _int(title.get("hoCnt")),
        "총주차": None if all(p is None for p in parking) else sum(p or 0 for p in parking),
        "승강기": _int(title.get("rideUseElvtCnt")),
        "사용승인일": _date(title.get("useAprDay")),
        "전용_sqm": excl_area,
        "공급_sqm": round(excl_area + comm_area, 4) if excl_area is not None else None,
        "물건종류": "집합건물" if unit_rows else "일반건물",
        "표제부_비고": note or None,
        # 소재지 비교용 (계약 확장)
        "대지위치": _str(title.get("platPlc")),
        "동명칭": _str(unit.get("dongNm")) or _str(title.get("dongNm")),
        "호명칭": _str(unit.get("hoNm")),
        "해당층": _floor(unit) if unit else None,
    }


def get_register(
    api_key: str,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    *,
    plat_gb_cd: str = "0",
    dong: str | None = None,
    ho: str | None = None,
    http_get: HttpGet = requests.get,
) -> dict[str, Any]:
    """주소 코드 → register dict. 실패는 HubError 계열로 던진다."""
    if not api_key:
        raise HubError("API 키가 없음 (DATA_GO_KR_API_KEY)")
    base = {"sigunguCd": sigungu_cd, "bjdongCd": bjdong_cd, "platGbCd": plat_gb_cd, "bun": bun, "ji": ji}

    titles, _ = _call(api_key, "getBrTitleInfo", {**base, "numOfRows": PAGE_SIZE, "pageNo": 1}, http_get)
    if not titles:
        raise RegisterNotFound("건축물대장 없음 (신축·멸실·지번 오류 가능)")
    title, note = select_title(titles, dong)

    if ho:
        rows, total = _fetch_unit(api_key, base, dong, ho, http_get)
        if rows:
            return build_register(title, rows, note)
        if total:
            raise HoNotFound(f"'{ho}' 호가 대장에 없음")
        note = " / ".join(n for n in (note, "전유부 없음 → 일반건물로 처리, 호 무시") if n)
        return build_register(title, None, note)

    probe, _ = _call(api_key, "getBrExposPubuseAreaInfo", {**base, "numOfRows": 1, "pageNo": 1}, http_get)
    if probe:
        raise HoRequired("집합건물 → 호 입력 필요")
    return build_register(title, None, note)
