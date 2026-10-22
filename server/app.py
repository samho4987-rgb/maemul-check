"""Flask API (설계 6.1).

    POST /api/verify   광고 + 주소 → 검수 결과 (+ 일 한도)
    GET  /api/ping     콜드스타트 워밍업

로컬:  .venv/bin/python -m server.app        (http://127.0.0.1:8000)
배포:  gunicorn server.app:app

환경변수 (여기서만 읽는다)
    DATA_GO_KR_API_KEY  건축HUB 키 (Decoding)
    QUOTA_LIMIT         일 한도, 기본 10
    QUOTA_DB            SQLite 경로, 기본 server/quota.db
    CORS_ORIGINS        허용 출처 쉼표 구분 (예: https://아이디.github.io). 비우면 전부 허용(로컬용)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from maemul_check import AdInput, __version__, verify
from maemul_check.cli import load_env
from maemul_check.pubdata import hub, regions

from .quota import Quota

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)

# 사용자가 고르면 다시 시도할 수 있는 오류 → 422 (candidates 포함)
NEEDS_INPUT = (hub.DongRequired, hub.HoRequired, hub.HoNotFound)


def _error(status: int, code: str, message: str = "", **extra: Any):
    return jsonify({"error": code, "message": message, **extra}), status


def _client_id(body: dict) -> str:
    token = body.get("client_token")
    if isinstance(token, str) and 0 < len(token) <= 64:
        return f"t:{token}"
    # Render 는 프록시 뒤에 있으므로 X-Forwarded-For 첫 값이 실제 IP
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    return f"ip:{ip}"


def create_app(config: dict[str, Any] | None = None) -> Flask:
    load_env(ROOT / ".env")
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.update(
        API_KEY=os.environ.get("DATA_GO_KR_API_KEY", ""),
        QUOTA_LIMIT=int(os.environ.get("QUOTA_LIMIT", "10")),
        QUOTA_DB=os.environ.get("QUOTA_DB", str(ROOT / "server" / "quota.db")),
        CORS_ORIGINS=os.environ.get("CORS_ORIGINS", ""),
        HTTP_GET=requests.get,   # 테스트에서 fixture 로 교체
    )
    app.config.update(config or {})

    origins = [o.strip() for o in app.config["CORS_ORIGINS"].split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins or "*"}})
    quota = Quota(app.config["QUOTA_DB"], app.config["QUOTA_LIMIT"])

    @app.get("/api/ping")
    def ping():
        return jsonify({"ok": True, "version": __version__})

    @app.post("/api/verify")
    def verify_ad():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _error(400, "bad_request", "JSON 본문이 필요함")
        address, ad = body.get("address"), body.get("ad")
        if not isinstance(address, dict) or not isinstance(ad, dict):
            return _error(400, "bad_request", "address 와 ad 객체가 필요함")

        try:
            parsed = regions.parse_address(f"{address.get('region') or ''} {address.get('jibun') or ''}".strip())
        except regions.RegionError as e:
            return _error(400, "bad_address", str(e))

        client = _client_id(body)
        if quota.exceeded(client):
            return _error(429, "daily_limit", "오늘 검수 한도를 다 썼음", quota=quota.status(client))

        dong, ho = address.get("dong") or None, address.get("ho") or None
        register_error = None
        try:
            register = hub.get_register(
                app.config["API_KEY"], parsed.region.sigungu_cd, parsed.region.bjdong_cd, parsed.bun, parsed.ji,
                plat_gb_cd=parsed.plat_gb_cd, dong=dong, ho=ho, http_get=app.config["HTTP_GET"],
            )
        except NEEDS_INPUT as e:
            return _error(422, e.code, str(e), candidates=e.candidates)
        except hub.RegisterNotFound as e:
            # 신축·멸실 등: 비교 항목은 조회불가, 누락 체크는 그대로 (설계 3.2)
            register, register_error = None, e.code
        except hub.HubError as e:
            log.warning("register lookup failed: %s", e)
            return _error(502, e.code, str(e), retry=e.retry)

        ad_input = AdInput.from_dict(ad, {"region": parsed.region.name, "jibun": parsed.jibun, "dong": dong, "ho": ho})
        report = verify(ad_input, register)
        return jsonify({**report.to_dict(), "register_error": register_error, "quota": quota.consume(client)})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "8000")), debug=False)
