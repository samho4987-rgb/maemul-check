"""server/ API. 건축HUB 는 fixture 로 대체 (실API 호출 없음)."""
import json
from datetime import datetime
from pathlib import Path

import pytest
import requests

from server.app import create_app
from server.quota import KST, Quota
from test_hub import KEY, fake_get

AD = json.loads((Path(__file__).parent.parent / "examples" / "ad.json").read_text(encoding="utf-8"))
BODY = {"address": {"region": "부산 수영구 광안동", "jibun": "170-5", "dong": None, "ho": "301"},
        "ad": AD, "client_token": "test-token"}
OK_ROUTES = {"getBrTitleInfo": "title_multi.json", "getBrExposPubuseAreaInfo": "expos_301.json"}


def client(tmp_path, routes=OK_ROUTES, limit=10):
    app = create_app({"API_KEY": KEY, "QUOTA_DB": str(tmp_path / "q.db"), "QUOTA_LIMIT": limit,
                      "HTTP_GET": fake_get(routes)})
    return app.test_client()


def test_ping(tmp_path):
    r = client(tmp_path).get("/api/ping")
    assert r.status_code == 200 and r.json["ok"] is True


def test_verify_200(tmp_path):
    r = client(tmp_path).post("/api/verify", json=BODY)
    assert r.status_code == 200
    assert len(r.json["items"]) == 14
    assert r.json["register_snapshot"]["전용_sqm"] == 29.75
    assert r.json["quota"]["used"] == 1 and r.json["quota"]["limit"] == 10
    assert r.json["quota"]["reset_at"].endswith("+09:00")


def test_daily_limit_429(tmp_path):
    c = client(tmp_path, limit=2)
    assert [c.post("/api/verify", json=BODY).status_code for _ in range(3)] == [200, 200, 429]
    r = c.post("/api/verify", json=BODY)
    assert r.json["error"] == "daily_limit" and r.json["quota"]["used"] == 2
    # 다른 토큰은 별도 한도
    assert c.post("/api/verify", json={**BODY, "client_token": "other"}).status_code == 200


def test_register_unavailable_502_does_not_consume(tmp_path):
    c = client(tmp_path, routes={"getBrTitleInfo": requests.ConnectionError("boom")})
    r = c.post("/api/verify", json=BODY)
    assert r.status_code == 502
    assert r.json["error"] == "register_unavailable" and r.json["retry"] is True
    assert KEY not in r.get_data(as_text=True)
    assert Quota(str(tmp_path / "q.db"), 10).status("t:test-token")["used"] == 0


def test_register_not_found_still_checks_missing(tmp_path):
    r = client(tmp_path, routes={"getBrTitleInfo": "empty.json"}).post("/api/verify", json=BODY)
    assert r.status_code == 200
    assert r.json["register_error"] == "register_not_found"
    assert r.json["items"][0]["status"] == "조회불가"


def test_ho_required_422(tmp_path):
    body = {**BODY, "address": {**BODY["address"], "ho": None}}
    r = client(tmp_path).post("/api/verify", json=body)
    assert r.status_code == 422 and r.json["error"] == "ho_required"


def test_dong_required_422_with_candidates(tmp_path):
    r = client(tmp_path, routes={"getBrTitleInfo": "title_two_dongs.json"}).post("/api/verify", json=BODY)
    assert r.status_code == 422 and r.json["error"] == "dong_required" and r.json["candidates"]


@pytest.mark.parametrize("body, code", [
    (None, "bad_request"),
    ({"address": {}, "ad": {}}, "bad_address"),
    ({"address": {"region": "없는동네", "jibun": "1"}, "ad": {}}, "bad_address"),
])
def test_bad_input_400(tmp_path, body, code):
    r = client(tmp_path).post("/api/verify", json=body)
    assert r.status_code == 400 and r.json["error"] == code


def test_quota_resets_at_kst_midnight(tmp_path):
    now = [datetime(2026, 10, 23, 23, 59, tzinfo=KST)]
    q = Quota(str(tmp_path / "q.db"), 1, now=lambda: now[0])
    q.consume("a")
    assert q.exceeded("a")
    assert q.status("a")["reset_at"] == "2026-10-24T00:00:00+09:00"
    now[0] = datetime(2026, 10, 24, 0, 0, tzinfo=KST)
    assert not q.exceeded("a")
