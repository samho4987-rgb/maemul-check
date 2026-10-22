"""1 소재지: 집합건물은 동·호, 일반건물은 지번 일치."""
from __future__ import annotations

import re

from ..schema import MATCH, MISMATCH, MISSING, UNAVAILABLE, Address, ItemResult

_JIBUN = re.compile(r"(산\s*)?(\d+)(?:\s*-\s*(\d+))?")


def parse_jibun(text: str | None) -> tuple[bool, int, int] | None:
    """"170-5" / "산 12" / "...광안동 170-5번지" → (산여부, 본번, 부번). 마지막 지번을 쓴다."""
    if not text:
        return None
    found = list(_JIBUN.finditer(text))
    if not found:
        return None
    m = found[-1]
    return bool(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def norm_dong(v: str | None) -> str:
    return (v or "").strip().removesuffix("동").strip()


def norm_ho(v: str | None) -> str:
    return (v or "").strip().removesuffix("호").strip().lstrip("0")


def _fmt_jibun(j: tuple[bool, int, int]) -> str:
    return f"{'산' if j[0] else ''}{j[1]}" + (f"-{j[2]}" if j[2] else "")


def compare_address(addr: Address, reg: dict) -> ItemResult:
    collective = reg.get("물건종류") == "집합건물"
    ad_text = " ".join(p for p in (addr.region, addr.jibun) if p) or None

    if collective:
        ad_dh = " ".join(p for p in (addr.dong and f"{norm_dong(addr.dong)}동", addr.ho and f"{norm_ho(addr.ho)}호") if p)
        reg_dong, reg_ho = reg.get("동명칭"), reg.get("호명칭")
        reg_dh = " ".join(p for p in (reg_dong, reg_ho and f"{norm_ho(reg_ho)}호") if p) or None
        ad_show = " ".join(p for p in (ad_text, ad_dh) if p) or None

        def result(status: str, note: str = "") -> ItemResult:
            return ItemResult("address", "소재지", ad_show, reg_dh, status, note)

        if not addr.ho:
            return result(MISSING, "집합건물은 호 기재 필요")
        if not reg_ho:
            return result(UNAVAILABLE, "대장 전유부 호 없음")
        if norm_ho(addr.ho) != norm_ho(reg_ho):
            return result(MISMATCH, "호 불일치")
        if reg_dong and norm_dong(addr.dong) and norm_dong(addr.dong) != norm_dong(reg_dong):
            return result(MISMATCH, "동 불일치")
        return result(MATCH)

    reg_plat = reg.get("대지위치")

    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("address", "소재지", ad_text, reg_plat, status, note)

    ad_j = parse_jibun(addr.jibun)
    if not addr.region or ad_j is None:
        return result(MISSING, "주소·지번 미기재")
    reg_j = parse_jibun(reg_plat)
    if reg_j is None:
        return result(UNAVAILABLE)
    if ad_j != reg_j:
        return result(MISMATCH, f"지번 {_fmt_jibun(ad_j)} ≠ {_fmt_jibun(reg_j)}")
    return result(MATCH)
