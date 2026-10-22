"""5 사용승인일: 년·월 일치, 일만 다르면 확인필요."""
from __future__ import annotations

import re

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult


def parse_date(text: str | None) -> tuple[int, int, int | None] | None:
    """"2018-03", "2018.03.15", "201803", "20180315" → (2018, 3, 15|None)."""
    if not text:
        return None
    s = text.strip()
    if re.fullmatch(r"\d{6}|\d{8}", s):
        parts = [s[:4], s[4:6]] + ([s[6:8]] if len(s) == 8 else [])
    else:
        parts = re.findall(r"\d+", s)
    if len(parts) < 2 or len(parts[0]) != 4:
        return None
    y, m = int(parts[0]), int(parts[1])
    d = int(parts[2]) if len(parts) > 2 else None
    if not 1 <= m <= 12 or (d is not None and not 1 <= d <= 31):
        return None
    return y, m, d


def compare_approval(ad_text: str | None, reg_text: str | None, tol: dict) -> ItemResult:
    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("approval_date", "사용승인일", ad_text, reg_text, status, note)

    if not ad_text:
        return result(MISSING, "광고 사용승인일 미기재")
    ad = parse_date(ad_text)
    if ad is None:
        return result(MISSING, "날짜 형식 아님 (예: 2018-03)")
    reg = parse_date(reg_text)
    if reg is None:
        return result(UNAVAILABLE)

    if ad[:2] != reg[:2]:
        return result(MISMATCH)
    if ad[2] is not None and reg[2] is not None and ad[2] != reg[2]:
        if tol.get("precision") == "day":
            return result(MISMATCH, "일 불일치")
        return result(CHECK, "년·월 일치, 일만 다름")
    return result(MATCH)
