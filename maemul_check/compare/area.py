"""2 전용면적: ±max(abs, rel) 이내 일치, check_rel 이내 확인필요."""
from __future__ import annotations

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult

SQM_PER_PYEONG = 3.305785
EPS = 1e-9


def fmt_area(m2: float | None) -> str | None:
    if m2 is None:
        return None
    return f"{m2:g}㎡ ({m2 / SQM_PER_PYEONG:.1f}평)"


def compare_area(ad_m2: float | None, reg_m2: float | None, tol: dict, *, collective: bool = True) -> ItemResult:
    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("area", "전용면적", fmt_area(ad_m2), fmt_area(reg_m2), status, note)

    if ad_m2 is None:
        return result(MISSING, "광고 전용면적 미기재")
    if reg_m2 is None:
        note = "대장에 전유면적 없음" if collective else "일반건물은 호별 전용면적이 대장에 없음"
        return result(UNAVAILABLE, note)

    diff = abs(ad_m2 - reg_m2)
    allowed = max(tol["abs_m2"], reg_m2 * tol["rel"])
    note = f"차이 {diff:.2f}㎡ (허용 ±{allowed:.2f}㎡)"
    if diff <= allowed + EPS:
        return result(MATCH, note)
    if diff <= reg_m2 * tol["check_rel"] + EPS:
        return result(CHECK, note)
    return result(MISMATCH, note)
