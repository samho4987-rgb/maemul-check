"""4 총층수: 지상층수 일치. 지하는 참고."""
from __future__ import annotations

from ..schema import MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult


def compare_floors(ad_floors: int | None, grnd: int | None, ugrnd: int | None) -> ItemResult:
    ad = f"{ad_floors}층" if ad_floors is not None else None
    reg = f"지상 {grnd}층" if grnd is not None else None
    note = f"지하 {ugrnd}층 (참고)" if ugrnd else ""

    if ad_floors is None:
        status, note = MISSING, "광고 총층수 미기재"
    elif grnd is None:
        status = UNAVAILABLE
    elif ad_floors == grnd:
        status = MATCH
    else:
        status = MISMATCH
    return ItemResult("floors_total", "총층수", ad, reg, status, note)
