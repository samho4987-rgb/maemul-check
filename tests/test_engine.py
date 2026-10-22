"""설계 3.4 더미 5건. 기준 광고·대장(전부 초록)에서 한 항목씩만 바꾼다."""
import copy

import pytest

from maemul_check import AdInput, verify
from maemul_check.schema import CHECK, MATCH, MISMATCH, MISSING, VERDICT_CHECK, VERDICT_FIX, VERDICT_OK

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
}

AD = {
    "kind": "오피스텔",
    "area_m2": 32.4,
    "deal_type": "월세",
    "deposit": 5_000_000,
    "rent": 500_000,
    "floors_total": 4,
    "approval_date": "2018-03",
    "direction": "남향",
    "rooms": 1,
    "baths": 1,
    "move_in": "즉시",
    "maint_fee": 70_000,
    "parking": 6,
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
