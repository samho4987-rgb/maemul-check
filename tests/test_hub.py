"""건축HUB 파싱. fixture 응답만 쓰고 실제 API 는 호출하지 않는다."""
from pathlib import Path

import pytest
import requests

from maemul_check.pubdata import hub, regions

FIXTURES = Path(__file__).parent / "fixtures"
KEY = "TEST-KEY-DO-NOT-LEAK"


class FakeResp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def fake_get(routes):
    """routes: {endpoint: fixture 파일명 또는 예외}. 호출 기록은 .calls"""
    calls = []

    def get(url, params=None, timeout=None):
        endpoint = url.rsplit("/", 1)[-1]
        calls.append((endpoint, params))
        r = routes[endpoint]
        if isinstance(r, Exception):
            raise r
        return FakeResp((FIXTURES / r).read_text(encoding="utf-8"))

    get.calls = calls
    return get


ADDR = ("26500", "10400", "0170", "0005")


def test_collective_unit_register():
    get = fake_get({"getBrTitleInfo": "title_multi.json", "getBrExposPubuseAreaInfo": "expos_301.json"})
    reg = hub.get_register(KEY, *ADDR, ho="301", http_get=get)

    assert reg["물건종류"] == "집합건물"
    assert reg["전용_sqm"] == 29.75
    assert reg["공급_sqm"] == pytest.approx(29.75 + 12.31 + 8.02)
    assert reg["호_용도"] == "오피스텔"
    assert reg["용도"] == "오피스텔,제2종근린생활시설"   # etcPurps 우선
    assert reg["지상층수"] == 15 and reg["지하층수"] == 2
    assert reg["총주차"] == 60
    assert reg["승강기"] == 2
    assert reg["사용승인일"] == "2018-03-15"
    assert reg["호명칭"] == "301호"
    assert "주건축물" in reg["표제부_비고"]
    assert get.calls[1][1]["hoNm"] == "301"
    assert get.calls[0][1]["serviceKey"] == KEY


def test_ho_required_for_collective():
    get = fake_get({"getBrTitleInfo": "title_multi.json", "getBrExposPubuseAreaInfo": "expos_301.json"})
    with pytest.raises(hub.HoRequired):
        hub.get_register(KEY, *ADDR, http_get=get)


def test_general_building_without_units():
    get = fake_get({"getBrTitleInfo": "title_multi.json", "getBrExposPubuseAreaInfo": "empty.json"})
    reg = hub.get_register(KEY, *ADDR, http_get=get)
    assert reg["물건종류"] == "일반건물"
    assert reg["전용_sqm"] is None


def test_multi_dong_requires_selection():
    get = fake_get({"getBrTitleInfo": "title_two_dongs.json"})
    with pytest.raises(hub.DongRequired) as e:
        hub.get_register(KEY, *ADDR, http_get=get)
    assert e.value.candidates == ["101동", "102동"]


def test_dong_selection():
    title, _ = hub.select_title(hub._parse((FIXTURES / "title_two_dongs.json").read_text())[0], dong="102")
    assert title["grndFlrCnt"] == 18


def test_no_register():
    get = fake_get({"getBrTitleInfo": "empty.json"})
    with pytest.raises(hub.RegisterNotFound):
        hub.get_register(KEY, *ADDR, http_get=get)


def test_key_error_xml():
    get = fake_get({"getBrTitleInfo": "key_error.xml"})
    with pytest.raises(hub.HubError, match="SERVICE_KEY_IS_NOT_REGISTERED"):
        hub.get_register(KEY, *ADDR, http_get=get)


def test_retry_then_fail_without_leaking_key():
    err = requests.ConnectionError(f"https://apis.data.go.kr/...?serviceKey={KEY}")
    get = fake_get({"getBrTitleInfo": err})
    with pytest.raises(hub.HubError) as e:
        hub.get_register(KEY, *ADDR, http_get=get)
    assert len(get.calls) == 1 + hub.RETRIES
    assert e.value.retry is True
    assert KEY not in str(e.value)


def test_parse_address():
    a = regions.parse_address("부산 수영구 광안동 170-5")
    assert (a.region.sigungu_cd, a.region.bjdong_cd, a.bun, a.ji, a.plat_gb_cd) == ("26500", "10400", "0170", "0005", "0")
    assert a.jibun == "170-5"
    assert regions.parse_address("부산 수영구 광안동 산 12").plat_gb_cd == "1"
