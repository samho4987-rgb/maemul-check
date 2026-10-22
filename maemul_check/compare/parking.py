"""6 주차대수: 건물 총대수 기준. 광고 < 대장 확인필요, > 불일치."""
from __future__ import annotations

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult


def compare_parking(ad_count: int | None, reg_total: int | None, households: int | None) -> ItemResult:
    ad = f"{ad_count}대" if ad_count is not None else None
    reg = f"{reg_total}대" if reg_total is not None else None
    per = f"세대당 {reg_total / households:.2f}대 (참고)" if reg_total is not None and households else ""

    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("parking", "주차대수", ad, reg, status, " / ".join(n for n in (note, per) if n))

    if ad_count is None:
        return result(MISSING, "광고 주차대수 미기재")
    if reg_total is None:
        return result(UNAVAILABLE)
    if ad_count == reg_total:
        return result(MATCH)
    if ad_count < reg_total:
        return result(CHECK, "광고값이 대장 총대수보다 작음 (세대당 표기인지 확인)")
    return result(MISMATCH, "광고값이 대장보다 큼")
