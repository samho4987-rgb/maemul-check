"""설계 3.4 더미 5건. 기준 광고·대장(전부 초록)에서 한 항목씩만 바꾼다."""
import copy

import pytest

from maemul_check import AdInput, verify
from maemul_check.schema import (
    CHECK,
    MATCH,
    MISMATCH,
    MISSING,
    PRESENT,
    UNAVAILABLE,
    VERDICT_CHECK,
    VERDICT_FIX,
    VERDICT_OK,
)

REGISTER = {
    "건물명": "더미오피스텔",
    "용도": "업무시설",
    "호_용도": "오피스텔",
    "구조": "철근콘크리트구조",
    "지상층수": 4,
    "지하층수": 1,
    "세대수": 6,
    "가구수": 0,
    "호수": 12,
    "총주차": 6,
    "승강기": 1,
    "사용승인일": "2018-03-15",
    "전용_sqm": 32.4,
    "공급_sqm": 45.1,
    "물건종류": "집합건물",
    "표제부_비고": None,
    "대지위치": "부산광역시 수영구 광안동 170-5번지",
    "동명칭": None,
    "호명칭": "301호",
    "해당층": 3,
}

AD = {
    "kind": "오피스텔",
    "area_m2": 32.4,
    "deal_type": "월세",
    "deposit": 5_000_000,
    "rent": 500_000,
    "floor": 3,
    "floors_total": 4,
    "approval_date": "2018-03",
    "direction": "남향",
    "direction_basis": "주실",
    "rooms": 1,
    "baths": 1,
    "move_in": "즉시",
    "maint_fee": 70_000,
    "parking": 6,
    "parking_unit": "총",
    "elevator": True,
    "office": {"name": "더미공인중개사사무소", "addr": "부산 수영구 광안로 1", "reg_no": "26500-2020-00001",
               "tel": "051-000-0000", "rep": "홍길동"},
}
ADDRESS = {"region": "부산 수영구 광안동", "jibun": "170-5", "dong": None, "ho": "301"}


def run(ad_patch=None, reg_patch=None):
    ad = {**copy.deepcopy(AD), **(ad_patch or {})}
    reg = {**REGISTER, **(reg_patch or {})}
    return verify(AdInput.from_dict(ad, ADDRESS), reg)


def test_baseline_all_green():
    report = run()
    assert report.verdict == VERDICT_OK, [(i.label, i.status, i.note) for i in report.items]
    assert len(report.items) == 14


def test_1_floors_mismatch():
    report = run(ad_patch={"floors_total": 5}, reg_patch={"지상층수": 4})
    assert report.item("floors_total").status == MISMATCH
    assert report.verdict == VERDICT_FIX


def test_2_parking_mismatch():
    report = run(ad_patch={"parking": 8}, reg_patch={"총주차": 6})
    assert report.item("parking").status == MISMATCH
    assert report.verdict == VERDICT_FIX


def test_3_oneroom_on_mixed_purpose_needs_check():
    report = run(
        ad_patch={"kind": "원룸"},
        reg_patch={"용도": "근린생활시설, 주택", "호_용도": None, "물건종류": "일반건물", "전용_sqm": None},
    )
    assert report.item("kind").status == CHECK


def test_4_area_within_tolerance():
    report = run(ad_patch={"area_m2": 32.6}, reg_patch={"전용_sqm": 32.4})
    assert report.item("area").status == MATCH


def test_5_office_reg_no_missing():
    office = {**AD["office"], "reg_no": ""}
    report = run(ad_patch={"office": office})
    item = report.item("office")
    assert item.status == MISSING
    assert "등록번호" in item.note
    assert report.verdict == VERDICT_FIX


@pytest.mark.parametrize("ad_m2, expected", [(32.9, MATCH), (33.0, CHECK), (33.2, MISMATCH)])
def test_area_bands(ad_m2, expected):
    # 32.4㎡ 기준: 허용 ±0.5 (1%=0.324 보다 큼), 확인필요 ±0.648 (2%)
    assert run(ad_patch={"area_m2": ad_m2}).item("area").status == expected


def test_register_unavailable_is_gray_and_check():
    report = verify(AdInput.from_dict(AD, ADDRESS), None)
    assert report.item("floors_total").status == "조회불가"
    assert report.verdict == VERDICT_CHECK


# ── 고시 제2024-748호 반영 (세션 2 ①) ─────────────────────────────

GENERAL = {"물건종류": "일반건물", "호_용도": None, "전용_sqm": None, "동명칭": None, "호명칭": None, "해당층": None}


@pytest.mark.parametrize("floor, expected", [
    (3, MATCH), ("3층", MATCH), (4, MISMATCH), ("지하1", MISMATCH),
    ("저", CHECK), ("저층", CHECK), (None, MISSING), ("꼭대기", MISSING),
])
def test_address_floor(floor, expected):
    assert run(ad_patch={"floor": floor}).item("address").status == expected


def test_address_basement_floor_match():
    assert run(ad_patch={"floor": "B1"}, reg_patch={"해당층": -1}).item("address").status == MATCH


def test_address_ho_is_not_compared():
    report = verify(AdInput.from_dict(AD, {**ADDRESS, "ho": None}), {**REGISTER, "호명칭": "302호"})
    assert report.item("address").status == MATCH


def test_address_jibun_mismatch_on_collective():
    report = verify(AdInput.from_dict(AD, {**ADDRESS, "jibun": "170-6"}), REGISTER)
    item = report.item("address")
    assert item.status == MISMATCH and "지번" in item.note


@pytest.mark.parametrize("dong, expected", [("101", MATCH), ("101동", MATCH), ("102", MISMATCH), (None, MISSING)])
def test_address_dong(dong, expected):
    report = verify(AdInput.from_dict(AD, {**ADDRESS, "dong": dong}), {**REGISTER, "동명칭": "101동"})
    assert report.item("address").status == expected


def test_address_general_building_needs_only_jibun():
    assert run(ad_patch={"floor": None}, reg_patch=GENERAL).item("address").status == MATCH


def test_address_worst_issue_wins():
    report = verify(AdInput.from_dict({**AD, "floor": "고"}, {**ADDRESS, "jibun": "1"}), REGISTER)
    item = report.item("address")
    assert item.status == MISMATCH
    assert "지번" in item.note and "고층" in item.note


@pytest.mark.parametrize("count, expected", [(0.5, MATCH), (0.4, CHECK), (0.6, MISMATCH), (1, MISMATCH)])
def test_parking_per_household(count, expected):
    # 총 6대 ÷ 세대수 12 = 0.5
    report = run(ad_patch={"parking": count, "parking_unit": "세대당"}, reg_patch={"세대수": 12})
    assert report.item("parking").status == expected


def test_parking_per_household_falls_back_to_ho_count():
    # 오피스텔: 세대수 0 → 호수 12 로 나눔
    report = run(ad_patch={"parking": 0.5, "parking_unit": "세대당"}, reg_patch={"세대수": 0, "호수": 12})
    assert report.item("parking").status == MATCH


def test_parking_total_less_needs_check():
    assert run(ad_patch={"parking": 5}).item("parking").status == CHECK


def test_parking_unit_missing():
    item = run(ad_patch={"parking_unit": None}).item("parking")
    assert item.status == MISSING and "세대당" in item.note


@pytest.mark.parametrize("direction, basis, expected", [
    ("남향", "주실", PRESENT), ("정남향", "거실 기준", PRESENT), ("남동향", "주출입구", PRESENT),
    ("남향", None, MISSING), (None, "주실", MISSING), ("앞향", "주실", MISSING),
])
def test_direction_needs_basis(direction, basis, expected):
    item = run(ad_patch={"direction": direction, "direction_basis": basis}).item("direction")
    assert item.status == expected


@pytest.mark.parametrize("fee, kind, expected", [
    (None, "상가", PRESENT), (None, "사무실", PRESENT), (None, "오피스텔", MISSING),
    (None, "아파트", MISSING), (99_999, "오피스텔", PRESENT), (100_000, "오피스텔", CHECK), (150_000, "상가", CHECK),
])
def test_maint_fee(fee, kind, expected):
    assert run(ad_patch={"maint_fee": fee, "kind": kind}).item("maint_fee").status == expected


@pytest.mark.parametrize("move_in, expected", [
    ("즉시", PRESENT), ("즉시입주", PRESENT), ("2026-11-15", PRESENT), ("2026년 11월", PRESENT),
    ("11월 초순", PRESENT), ("2026년 12월 하순", PRESENT), ("협의", MISSING), ("초순", MISSING), (None, MISSING),
])
def test_move_in(move_in, expected):
    assert run(ad_patch={"move_in": move_in}).item("move_in").status == expected


def test_register_unavailable_keeps_new_missing_checks():
    ad = {**AD, "parking_unit": None, "direction_basis": None}
    report = verify(AdInput.from_dict(ad, ADDRESS), None)
    assert report.item("address").status == UNAVAILABLE
    assert report.item("parking").status == MISSING      # 단위 미기재는 대장 없이도 누락
    assert report.item("direction").status == MISSING
