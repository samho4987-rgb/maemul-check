"""터미널 검수기.

    python -m maemul_check "부산 수영구 광안동 170-5" --ho 301 --ad examples/ad.json

--ad 없이 실행하면 건축물대장 요약만 보여준다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path

from .engine import verify
from .pubdata import hub, regions
from .schema import GRAY, GREEN, RED, YELLOW, AdInput, Report

DISCLAIMER = "※ 참고 자료이며 광고 등록 및 법적 판단 책임은 이용자에게 있음"


def load_env(path: Path = Path(".env")) -> None:
    """.env 의 KEY=VALUE 를 환경변수로 (이미 있으면 덮어쓰지 않음)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


# ── 출력 ────────────────────────────────────────────────────────

def _width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - _width(s))


def _color(status: str, text: str, on: bool) -> str:
    if not on:
        return text
    code = "32" if status in GREEN else "33" if status in YELLOW else "31" if status in RED else "90" if status in GRAY else "0"
    return f"\033[{code}m{text}\033[0m"


def render(report: Report, color: bool) -> str:
    head = ("검사항목", "광고값", "대장값", "판정", "비고")
    rows = [(i.label, i.ad or "-", i.register or "-", i.status, i.note) for i in report.items]
    w = [max(_width(r[c]) for r in [head, *rows]) for c in range(4)]
    line = "  ".join("─" * x for x in w) + "  " + "─" * 10
    out = ["  ".join(_pad(h, w[c]) for c, h in enumerate(head[:4])) + "  " + head[4], line]
    for r, item in zip(rows, report.items):
        cells = [_pad(r[c], w[c]) for c in range(4)]
        cells[3] = _color(item.status, cells[3], color)
        out.append("  ".join(cells) + "  " + r[4])
    out.append(line)
    verdict_status = "누락" if report.verdict == "수정 필요" else "확인필요" if report.verdict == "확인 권장" else "일치"
    out.append(f"종합 판정: {_color(verdict_status, report.verdict, color)}")
    out.append(DISCLAIMER)
    return "\n".join(out)


def render_register(reg: dict) -> str:
    w = max(_width(k) for k in reg)
    return "\n".join(f"{_pad(k, w)}  {'-' if v is None else v}" for k, v in reg.items())


# ── main ───────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="maemul_check", description="부동산 광고 명시사항 ↔ 건축물대장 검수")
    p.add_argument("address", help='주소 (예: "부산 수영구 광안동 170-5")')
    p.add_argument("--dong", help="동 (여러 동 건물)")
    p.add_argument("--ho", help="호 (집합건물)")
    p.add_argument("--ad", type=Path, help="광고 입력 JSON (설계 6.1의 ad 형식)")
    p.add_argument("--json", action="store_true", help="JSON 으로 출력")
    args = p.parse_args(argv)

    load_env()
    api_key = os.environ.get("DATA_GO_KR_API_KEY", "")

    try:
        addr = regions.parse_address(args.address)
    except regions.RegionError as e:
        print(f"주소 오류: {e}", file=sys.stderr)
        return 2

    if not args.json:
        print(f"조회: {addr.region.name} {addr.jibun}"
              f"{' ' + args.dong + '동' if args.dong else ''}{' ' + args.ho + '호' if args.ho else ''}"
              f"  (sigunguCd={addr.region.sigungu_cd} bjdongCd={addr.region.bjdong_cd})\n", flush=True)

    try:
        register = hub.get_register(
            api_key, addr.region.sigungu_cd, addr.region.bjdong_cd, addr.bun, addr.ji,
            plat_gb_cd=addr.plat_gb_cd, dong=args.dong, ho=args.ho,
        )
    except hub.HubError as e:
        print(f"대장 조회 실패: {e}", file=sys.stderr)
        if e.candidates:
            print(f"후보: {', '.join(e.candidates)}", file=sys.stderr)
        if not args.ad:
            return 3
        register = None

    if not args.ad:
        print(json.dumps(register, ensure_ascii=False, indent=2) if args.json else render_register(register))
        return 0

    raw = json.loads(args.ad.read_text(encoding="utf-8"))
    ad_dict = raw.get("ad", raw)
    address = {"region": addr.region.name, "jibun": addr.jibun, "dong": args.dong, "ho": args.ho}
    report = verify(AdInput.from_dict(ad_dict, address), register)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render(report, color=sys.stdout.isatty()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
