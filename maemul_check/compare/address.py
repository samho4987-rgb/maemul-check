"""1 소재지 (고시 제2024-748호): 지번 일치 + 집합건물은 동·해당층 일치.

호수는 명시사항이 아니다 (대장 조회용 입력일 뿐). 해당층은 저/중/고 대체 가능 → 확인필요.
"""
from __future__ import annotations

import re

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, Address, ItemResult

_JIBUN = re.compile(r"(산\s*)?(\d+)(?:\s*-\s*(\d+))?")
_BASEMENT = re.compile(r"(?:지하|B)\s*(\d+)", re.I)
FLOOR_BANDS = ("저", "중", "고")

# 여러 문제가 겹치면 앞쪽이 대표 판정
_SEVERITY = (MISSING, MISMATCH, CHECK, UNAVAILABLE)


def parse_jibun(text: str | None) -> tuple[bool, int, int] | None:
    """"170-5" / "산 12" / "...광안동 170-5번지" → (산여부, 본번, 부번). 마지막 지번을 쓴다."""
    if not text:
        return None
    found = list(_JIBUN.finditer(text))
    if not found:
        return None
    m = found[-1]
    return bool(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def parse_floor(v: int | str | None) -> int | str | None:
    """3 / "3층" / "지하1" / "B1" → 정수(지하는 음수), "저층"·"중"·"고" → "저"/"중"/"고"."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip().removesuffix("층").strip()
    if s in FLOOR_BANDS:
        return s
    m = _BASEMENT.fullmatch(s)
    if m:
        return -int(m.group(1))
    s = s.removeprefix("지상").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def fmt_floor(f: int | str | None) -> str | None:
    if f is None:
        return None
    if isinstance(f, str):
        return f"{f}층"
    return f"지하{-f}층" if f < 0 else f"{f}층"


def norm_dong(v: str | None) -> str:
    return (v or "").strip().removesuffix("동").strip()


def _fmt_jibun(j: tuple[bool, int, int]) -> str:
    return f"{'산' if j[0] else ''}{j[1]}" + (f"-{j[2]}" if j[2] else "")


def _join(*parts: str | None) -> str | None:
    return " ".join(p for p in parts if p) or None


def compare_address(addr: Address, floor: int | str | None, reg: dict) -> ItemResult:
    collective = reg.get("물건종류") == "집합건물"
    ad_j, reg_j = parse_jibun(addr.jibun), parse_jibun(reg.get("대지위치"))
    ad_f, reg_f = parse_floor(floor), reg.get("해당층")
    reg_dong = reg.get("동명칭")

    ad_show = _join(addr.region, addr.jibun, addr.dong and f"{norm_dong(addr.dong)}동", fmt_floor(ad_f) or (floor and str(floor)))
    reg_show = _join(reg_j and _fmt_jibun(reg_j), reg_dong, fmt_floor(reg_f) if collective else None)
    issues: list[tuple[str, str]] = []

    # 지번
    if not addr.region or ad_j is None:
        issues.append((MISSING, "주소·지번 미기재"))
    elif reg_j is None:
        issues.append((UNAVAILABLE, "대장 지번 없음"))
    elif ad_j != reg_j:
        issues.append((MISMATCH, f"지번 {_fmt_jibun(ad_j)} ≠ {_fmt_jibun(reg_j)}"))

    if collective:
        # 동
        if reg_dong and not norm_dong(addr.dong):
            issues.append((MISSING, "동 기재 필요"))
        elif reg_dong and norm_dong(addr.dong) != norm_dong(reg_dong):
            issues.append((MISMATCH, "동 불일치"))
        # 해당층
        if floor is not None and ad_f is None:
            issues.append((MISSING, "층수 형식 아님 (예: 3, 지하1, 저/중/고)"))
        elif ad_f is None:
            issues.append((MISSING, "해당층 기재 필요 (저/중/고 대체 가능)"))
        elif isinstance(ad_f, str):
            issues.append((CHECK, f"{ad_f}층 표기 → 대장 {fmt_floor(reg_f) or '해당층 없음'} 기준으로 확인"))
        elif reg_f is None:
            issues.append((UNAVAILABLE, "대장 해당층 없음"))
        elif ad_f != reg_f:
            issues.append((MISMATCH, f"해당층 {fmt_floor(ad_f)} ≠ {fmt_floor(reg_f)}"))

    if not issues:
        return ItemResult("address", "소재지", ad_show, reg_show, MATCH)
    worst = min(_SEVERITY.index(s) for s, _ in issues)
    return ItemResult("address", "소재지", ad_show, reg_show, _SEVERITY[worst], " / ".join(n for _, n in issues))
