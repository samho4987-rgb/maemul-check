"""입력(AdInput)·출력(Report, ItemResult) 데이터 구조."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

# 판정 등급 (설계 3.2)
MATCH = "일치"
PRESENT = "기재"
CHECK = "확인필요"
MISMATCH = "불일치"
MISSING = "누락"
UNAVAILABLE = "조회불가"

GREEN = {MATCH, PRESENT}
YELLOW = {CHECK}
RED = {MISMATCH, MISSING}
GRAY = {UNAVAILABLE}

VERDICT_FIX = "수정 필요"
VERDICT_CHECK = "확인 권장"
VERDICT_OK = "게시 가능"


@dataclass
class Address:
    region: str = ""          # "부산 수영구 광안동"
    jibun: str = ""           # "170-5"
    dong: str | None = None   # 집합건물 동
    ho: str | None = None     # 집합건물 호


@dataclass
class Office:
    name: str = ""     # 명칭
    addr: str = ""     # 소재지
    reg_no: str = ""   # 등록번호
    tel: str = ""      # 연락처
    rep: str = ""      # 대표자


@dataclass
class AdInput:
    """광고에 적을 명시사항 14항목."""
    address: Address = field(default_factory=Address)  # 1 소재지 (지번·동. 호는 대장 조회용)
    floor: int | str | None = None                     #   해당층 3 / "지하1" / "저"·"중"·"고"
    area_m2: float | None = None                       # 2 전용면적
    kind: str | None = None                            # 3 종류
    floors_total: int | None = None                    # 4 총층수
    approval_date: str | None = None                   # 5 사용승인일 "YYYY-MM" 또는 "YYYY-MM-DD"
    parking: float | None = None                       # 6 주차대수
    parking_unit: str | None = None                    #   "총" 또는 "세대당"
    elevator: bool | None = None                       # 7 승강기
    price: int | None = None                           # 8 가격(매매가)
    deposit: int | None = None                         #   보증금(전세·월세)
    rent: int | None = None                            #   월세
    deal_type: str | None = None                       # 9 거래형태
    direction: str | None = None                       # 10 방향 (8방위)
    direction_basis: str | None = None                 #    기준 "주실"(거실·안방) / "주출입구"
    rooms: int | None = None                           # 11 방 수
    baths: int | None = None                           #    욕실 수
    move_in: str | None = None                         # 12 입주가능일
    maint_fee: int | None = None                       # 13 관리비(원)
    office: Office = field(default_factory=Office)     # 14 중개사무소

    @classmethod
    def from_dict(cls, ad: dict[str, Any], address: dict[str, Any] | None = None) -> "AdInput":
        """API·JSON 형식(설계 6.1)에서 생성. 모르는 키는 무시."""
        names = {f.name for f in fields(cls)} - {"address", "office"}
        kwargs = {k: v for k, v in ad.items() if k in names}
        office_keys = {f.name for f in fields(Office)}
        addr_keys = {f.name for f in fields(Address)}
        kwargs["office"] = Office(**{k: v or "" for k, v in (ad.get("office") or {}).items() if k in office_keys})
        addr = address if address is not None else ad.get("address") or {}
        kwargs["address"] = Address(**{k: v for k, v in addr.items() if k in addr_keys})
        return cls(**kwargs)


@dataclass
class ItemResult:
    key: str
    label: str
    ad: str | None
    register: str | None
    status: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    verdict: str
    items: list[ItemResult]
    register_snapshot: dict[str, Any] | None = None

    def item(self, key: str) -> ItemResult:
        return next(i for i in self.items if i.key == key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "items": [i.to_dict() for i in self.items],
            "register_snapshot": self.register_snapshot,
        }
