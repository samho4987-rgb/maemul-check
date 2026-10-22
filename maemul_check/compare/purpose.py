"""3 종류: 광고 종류 ↔ 대장 주용도 (rules/purpose_map.json)."""
from __future__ import annotations

import re

from ..schema import CHECK, MATCH, MISMATCH, MISSING, UNAVAILABLE, ItemResult

_SPLIT = re.compile(r"[,，、·;]")


def split_purposes(text: str) -> list[str]:
    return [t.strip() for t in _SPLIT.split(text) if t.strip()]


def resolve_kind(kind: str, pmap: dict) -> str | None:
    kind = kind.strip()
    if kind in pmap["kinds"]:
        return kind
    return pmap["aliases"].get(kind)


def _hits(tokens: list[str], names: list[str]) -> list[str]:
    return [t for t in tokens if any(n in t for n in names)]


def compare_kind(ad_kind: str | None, reg_purpose: str | None, pmap: dict) -> ItemResult:
    def result(status: str, note: str = "") -> ItemResult:
        return ItemResult("kind", "종류", ad_kind, reg_purpose, status, note)

    if not ad_kind:
        return result(MISSING, "광고 종류 미기재")
    if not reg_purpose:
        return result(UNAVAILABLE, "대장 용도 없음")

    kind = resolve_kind(ad_kind, pmap)
    if kind is None:
        return result(CHECK, "매핑표에 없는 종류 → 대장 용도 직접 확인")

    rule = pmap["kinds"][kind]
    tokens = split_purposes(reg_purpose)
    hit = _hits(tokens, rule["allow"])
    soft = _hits(tokens, rule.get("check", []))

    if rule.get("always_check"):
        base = f"'{kind}'은 법적 종류가 아님 → 대장 용도 확인"
        return result(CHECK, base + (f" (허용 용도: {', '.join(hit)})" if hit else " (허용 용도 없음)"))
    if hit and len(hit) == len(tokens):
        return result(MATCH)
    if hit:
        return result(CHECK, f"복수 용도 중 일부만 해당: {', '.join(hit)}")
    if soft:
        return result(CHECK, f"'{', '.join(soft)}'은 '{kind}'로 쓰일 수 있으나 확인 필요")
    return result(MISMATCH, f"'{kind}' 허용 용도: {', '.join(rule['allow'])}")
