"""6 주차대수 (고시 제2024-748호): 총 주차대수 또는 세대당 주차대수를 구분 표시.

총이면 대장 합계와, 세대당이면 합계 ÷ 세대수(소수 1자리)와 비교.
광고 = 대장 일치, 광고 < 대장 확인필요, 광고 > 대장 불일치. 단위 미기재 → 누락.
"""
from __future__ import annotations

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult

UNIT_TOTAL = "총"
UNIT_PER = "세대당"
_UNIT_ALIASES = {"총": UNIT_TOTAL, "총대수": UNIT_TOTAL, "총주차대수": UNIT_TOTAL,
                 "세대당": UNIT_PER, "세대": UNIT_PER, "호당": UNIT_PER}


def norm_unit(v: str | None) -> str | None:
    return _UNIT_ALIASES.get((v or "").replace(" ", ""))


def _n(v: float) -> str:
    return f"{v:g}"


def compare_parking(
    ad_count: float | None,
    ad_unit: str | None,
    reg_total: int | None,
    households: int | None,
    units: int | None = None,
) -> ItemResult:
    unit = norm_unit(ad_unit)
    ad = None if ad_count is None else f"{'세대당 ' if unit == UNIT_PER else '총 ' if unit else ''}{_n(ad_count)}대"

    # 세대수 0 인 오피스텔 등은 호수로 나눈다
    denom, denom_label = (households, "세대수") if households else (units, "호수")
    per = round(reg_total / denom, 1) if reg_total is not None and denom else None
    reg = None if reg_total is None else f"총 {reg_total}대" + (f" (세대당 {_n(per)}대)" if per is not None else "")

    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("parking", "주차대수", ad, reg, status, note)

    if ad_count is None:
        return result(MISSING, "광고 주차대수 미기재")
    if unit is None:
        return result(MISSING, "총 / 세대당 구분 표시 필요")
    if reg_total is None:
        return result(UNAVAILABLE)

    if unit == UNIT_TOTAL:
        target, label = reg_total, "총대수"
    else:
        if per is None:
            return result(UNAVAILABLE, "대장 세대수·호수 없음 → 세대당 환산 불가")
        target, label = per, f"세대당(총 {reg_total} ÷ {denom_label} {denom})"
    value = round(ad_count, 1)

    if value == target:
        return result(MATCH)
    if value < target:
        return result(CHECK, f"광고값이 대장 {label}보다 작음")
    return result(MISMATCH, f"광고값이 대장 {label}보다 큼")
