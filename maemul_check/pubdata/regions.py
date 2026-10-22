"""법정동코드 검색: 주소 문자열 → sigunguCd(5) + bjdongCd(5) + 지번.

resources/region_codes.txt = 행정안전부 법정동코드 전체자료 중 '존재' 행만 (탭 구분, UTF-8).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REGION_FILE = Path(__file__).parent / "resources" / "region_codes.txt"

_JIBUN = re.compile(r"^(산)?\s*(\d+)(?:-(\d+))?(?:번지)?$")


@dataclass
class Region:
    code: str   # 10자리
    name: str   # "부산광역시 수영구 광안동"

    @property
    def sigungu_cd(self) -> str:
        return self.code[:5]

    @property
    def bjdong_cd(self) -> str:
        return self.code[5:]


@dataclass
class ParsedAddress:
    region: Region
    plat_gb_cd: str   # 0=대지, 1=산
    bun: str          # 4자리 0패딩
    ji: str           # 4자리 0패딩

    @property
    def jibun(self) -> str:
        j = f"{'산' if self.plat_gb_cd == '1' else ''}{int(self.bun)}"
        return j + (f"-{int(self.ji)}" if int(self.ji) else "")


class RegionError(ValueError):
    pass


@cache
def _rows() -> list[Region]:
    rows = []
    with REGION_FILE.open(encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) >= 3 and parts[2] == "존재":
                rows.append(Region(parts[0], parts[1]))
    return rows


def search(query: str) -> list[Region]:
    """모든 토큰을 포함하는 법정동(읍면동·리 단위)을 짧은 이름 순으로."""
    tokens = query.split()
    if not tokens:
        return []
    found = [r for r in _rows() if r.bjdong_cd != "00000" and all(t in r.name for t in tokens)]
    # 마지막 토큰이 이름 끝과 정확히 맞는 것 우선, 그다음 짧은 이름
    return sorted(found, key=lambda r: (r.name.split()[-1] != tokens[-1], len(r.name)))


def parse_address(text: str) -> ParsedAddress:
    """"부산 수영구 광안동 170-5" → ParsedAddress. 지번은 마지막 토큰."""
    tokens = text.split()
    if len(tokens) < 2:
        raise RegionError("주소는 '시군구 읍면동 지번' 형식 (예: 부산 수영구 광안동 170-5)")
    # "산 12-3" 처럼 띄어 쓴 경우
    if len(tokens) >= 3 and tokens[-2] == "산":
        tokens = tokens[:-2] + ["산" + tokens[-1]]
    m = _JIBUN.match(tokens[-1])
    if not m:
        raise RegionError(f"지번을 찾을 수 없음: '{tokens[-1]}'")
    matches = search(" ".join(tokens[:-1]))
    if not matches:
        raise RegionError(f"법정동을 찾을 수 없음: '{' '.join(tokens[:-1])}'")
    return ParsedAddress(
        region=matches[0],
        plat_gb_cd="1" if m.group(1) else "0",
        bun=m.group(2).zfill(4),
        ji=(m.group(3) or "0").zfill(4),
    )
