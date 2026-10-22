"""verify(ad, register) -> Report. 순수 함수, 네트워크 없음.

register 는 pubdata.hub.get_register() 가 만드는 dict (설계 4절 계약, 키는 한글).
대장을 못 가져온 경우 register=None → 비교 항목은 전부 조회불가.
"""
from __future__ import annotations

import re
from typing import Any

from . import rules
from .compare import (
    compare_address,
    compare_approval,
    compare_area,
    compare_floors,
    compare_kind,
    compare_parking,
)
from .schema import (
    CHECK,
    GRAY,
    MATCH,
    MISMATCH,
    MISSING,
    PRESENT,
    RED,
    UNAVAILABLE,
    VERDICT_CHECK,
    VERDICT_FIX,
    VERDICT_OK,
    YELLOW,
    AdInput,
    ItemResult,
    Report,
)


def verify(ad: AdInput, register: dict[str, Any] | None) -> Report:
    reg = register or {}
    tol = rules.load("tolerance")
    req = rules.load("required")
    collective = reg.get("물건종류") == "집합건물"

    items = [
        compare_address(ad.address, reg),
        compare_area(ad.area_m2, reg.get("전용_sqm"), tol["area"], collective=collective),
        compare_kind(ad.kind, reg.get("호_용도") or reg.get("용도"), rules.load("purpose_map")),
        compare_floors(ad.floors_total, reg.get("지상층수"), reg.get("지하층수")),
        compare_approval(ad.approval_date, reg.get("사용승인일"), tol["approval_date"]),
        compare_parking(ad.parking, reg.get("총주차"), reg.get("세대수")),
        _check_elevator(ad.elevator, reg.get("승강기")),
        _check_price(ad, req),
        _check_deal_type(ad.deal_type, req),
        _check_direction(ad.direction, req),
        _check_rooms(ad.rooms, ad.baths),
        _check_move_in(ad.move_in, req),
        _check_maint_fee(ad.maint_fee, req),
        _check_office(ad, req),
    ]
    if register is None:
        items = [_unavailable(i) if i.status not in RED else i for i in items[:7]] + items[7:]
    return Report(verdict=overall(items), items=items, register_snapshot=register)


def overall(items: list[ItemResult]) -> str:
    """빨강 ≥1 → 수정 필요 / 노랑·회색 → 확인 권장 / 전부 초록 → 게시 가능."""
    statuses = {i.status for i in items}
    if statuses & RED:
        return VERDICT_FIX
    if statuses & (YELLOW | GRAY):
        return VERDICT_CHECK
    return VERDICT_OK


def _unavailable(item: ItemResult) -> ItemResult:
    item.status, item.note = UNAVAILABLE, "건축물대장 조회 실패"
    return item


# ── 7 승강기 (비교) ─────────────────────────────────────────────

def _check_elevator(ad_has: bool | None, reg_count: int | None) -> ItemResult:
    ad = None if ad_has is None else ("있음" if ad_has else "없음")
    reg = None if reg_count is None else (f"있음({reg_count}대)" if reg_count > 0 else "없음")
    if ad_has is None:
        status = MISSING
    elif reg_count is None:
        status = UNAVAILABLE
    else:
        status = MATCH if ad_has == (reg_count > 0) else MISMATCH
    return ItemResult("elevator", "승강기", ad, reg, status)


# ── 8~14 누락 체크 ─────────────────────────────────────────────

def _present(v: Any) -> bool:
    return v is not None and str(v).strip() != ""


def _won(v: int) -> str:
    return f"{v:,}원"


def _check_price(ad: AdInput, req: dict) -> ItemResult:
    fields = req["price_fields"].get(ad.deal_type or "")
    if fields is None:
        return ItemResult("price", "가격", None, None, MISSING, "거래형태 미기재로 가격 판정 불가")
    shown = [f"{label} {_won(getattr(ad, k))}" for k, label in fields.items() if _present(getattr(ad, k))]
    lacking = [label for k, label in fields.items() if not _present(getattr(ad, k))]
    if lacking:
        return ItemResult("price", "가격", " / ".join(shown) or None, None, MISSING, f"{', '.join(lacking)} 누락")
    return ItemResult("price", "가격", " / ".join(shown), None, PRESENT)


def _check_deal_type(v: str | None, req: dict) -> ItemResult:
    ok = v in req["deal_types"]
    note = "" if ok else f"{'/'.join(req['deal_types'])} 중 하나"
    return ItemResult("deal_type", "거래형태", v, None, PRESENT if ok else MISSING, note)


def _check_direction(v: str | None, req: dict) -> ItemResult:
    core = (v or "").strip().removeprefix("정").removesuffix("향")
    ok = core in req["directions"]
    return ItemResult("direction", "방향", v, None, PRESENT if ok else MISSING, "" if ok else "8방위로 기재 (예: 남향)")


def _check_rooms(rooms: int | None, baths: int | None) -> ItemResult:
    ok = isinstance(rooms, int) and isinstance(baths, int) and rooms >= 0 and baths >= 0
    ad = f"방 {rooms} / 욕실 {baths}" if _present(rooms) or _present(baths) else None
    return ItemResult("rooms", "방·욕실 수", ad, None, PRESENT if ok else MISSING, "" if ok else "방·욕실 수 모두 정수로")


_DATE = re.compile(r"\d{4}\s*[-./년]\s*\d{1,2}")


def _check_move_in(v: str | None, req: dict) -> ItemResult:
    s = (v or "").strip()
    ok = bool(_DATE.match(s)) or any(s.startswith(w) for w in req["move_in_words"])
    return ItemResult("move_in", "입주가능일", v, None, PRESENT if ok else MISSING, "" if ok else "날짜 또는 즉시/협의")


def _check_maint_fee(v: int | None, req: dict) -> ItemResult:
    if not isinstance(v, int):
        return ItemResult("maint_fee", "관리비", None, None, MISSING, "금액 기재 (없으면 0)")
    limit = req["maint_fee_detail_threshold"]
    if v >= limit:
        return ItemResult("maint_fee", "관리비", _won(v), None, CHECK, f"{_won(limit)} 이상 → 세부내역 표시 필요")
    return ItemResult("maint_fee", "관리비", _won(v), None, PRESENT)


def _check_office(ad: AdInput, req: dict) -> ItemResult:
    labels = req["office_fields"]
    lacking = [label for k, label in labels.items() if not _present(getattr(ad.office, k))]
    shown = ad.office.name or None
    if lacking:
        return ItemResult("office", "중개사무소 정보", shown, None, MISSING, f"{', '.join(lacking)} 누락")
    return ItemResult("office", "중개사무소 정보", shown, None, PRESENT)

