from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from bot.config import Settings
from bot.database import Database
from bot.services.event_announcer import IngameEventAnnouncer
from bot.services.ingame_events import IngameEventService


def _verify_signature(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    if not secret or not timestamp or not signature:
        return False
    signed_payload = f"{timestamp}.".encode("utf-8") + body
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_timestamp_fresh(timestamp: str, tolerance_seconds: int = 300) -> bool:
    try:
        request_ts = int(timestamp)
    except ValueError:
        return False
    now_ts = int(datetime.now(timezone.utc).timestamp())
    return abs(now_ts - request_ts) <= tolerance_seconds


def create_api_app(
    db: Database,
    settings: Settings,
    announcer: IngameEventAnnouncer | None = None,
) -> FastAPI:
    app = FastAPI(title="BotCasino Ingame API", version="0.1.0")
    event_service = IngameEventService(db=db, referral_percent=settings.referral_percent)
    if settings.dev_disable_signature:
        logging.warning(
            "DEV_DISABLE_SIGNATURE is enabled. API authentication is bypassed and must not be used in production."
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="replace")
        if len(body_text) > 2000:
            body_text = body_text[:2000] + "...<truncated>"
        logging.error(
            "422 validation error on %s %s | body=%s | errors=%s",
            request.method,
            request.url.path,
            body_text,
            exc.errors(),
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    class RewardCreateRequest(BaseModel):
        gamer_id: str = Field(alias="gamerId")
        reward_id: str | None = None
        reward: dict[str, Any]

        model_config = ConfigDict(populate_by_name=True)

    class RewardCollectRequest(BaseModel):
        gamer_id: str = Field(alias="gamerId")
        reward_id: str = Field(alias="rewardId")

        model_config = ConfigDict(populate_by_name=True)

    class RewardResponse(BaseModel):
        reward_id: str
        gamer_id: str
        reward: dict[str, Any]
        collected: bool
        created_at: str
        collected_at: str | None

        model_config = ConfigDict(extra="forbid")

    def _normalize_gamer_id(value: str) -> str:
        return value.strip().upper()

    def _row_to_reward_response(row: Any) -> RewardResponse:
        payload = str(row["reward_json"] or "{}")
        try:
            reward_data = json.loads(payload)
            if not isinstance(reward_data, dict):
                reward_data = {"value": reward_data}
        except json.JSONDecodeError:
            reward_data = {}
        return RewardResponse(
            reward_id=str(row["reward_id"]),
            gamer_id=str(row["gamer_id"]),
            reward=reward_data,
            collected=bool(int(row["collected"])),
            created_at=str(row["created_at"]),
            collected_at=str(row["collected_at"]) if row["collected_at"] else None,
        )

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/rewards/{gamer_id}")
    @app.get("/rewards/{gamer_id}")
    async def get_rewards(
        gamer_id: str,
        collected: bool | None = None,
    ) -> dict[str, object]:
        normalized_gamer_id = _normalize_gamer_id(gamer_id)
        rows = db.get_player_rewards(normalized_gamer_id, collected=collected)
        rewards = [_row_to_reward_response(row).model_dump() for row in rows]
        return {
            "gamer_id": normalized_gamer_id,
            "count": len(rewards),
            "rewards": rewards,
        }

    @app.post("/v1/rewards/grant")
    @app.post("/rewards/grant")
    async def create_reward(payload: RewardCreateRequest) -> dict[str, object]:
        gamer_id = _normalize_gamer_id(payload.gamer_id)
        reward_id = (payload.reward_id or "").strip() or str(uuid.uuid4())
        created = db.create_player_reward(
            reward_id=reward_id,
            gamer_id=gamer_id,
            reward=payload.reward,
        )
        if not created:
            raise HTTPException(status_code=409, detail="reward_id_already_exists")
        return {
            "created": True,
            "reward_id": reward_id,
            "gamer_id": gamer_id,
        }

    @app.post("/v1/rewards")
    @app.post("/rewards")
    async def collect_reward(request: Request) -> dict[str, object]:
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="replace")

        payload_map: dict[str, Any] = {}
        content_type = request.headers.get("content-type", "").lower()
        try:
            if "application/json" in content_type:
                parsed = json.loads(body_text) if body_text else {}
                if isinstance(parsed, dict):
                    payload_map = parsed
                elif isinstance(parsed, str):
                    reparsed = json.loads(parsed)
                    payload_map = reparsed if isinstance(reparsed, dict) else {}
            elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form = await request.form()
                payload_map = dict(form)
            else:
                parsed = json.loads(body_text) if body_text else {}
                payload_map = parsed if isinstance(parsed, dict) else {}
        except Exception:
            payload_map = {}

        gamer_id_raw = str(
            payload_map.get("gamer_id")
            or payload_map.get("gamerId")
            or ""
        ).strip()
        reward_id_raw = str(
            payload_map.get("reward_id")
            or payload_map.get("rewardId")
            or ""
        ).strip()
        if not gamer_id_raw or not reward_id_raw:
            logging.error(
                "collect_reward invalid payload on %s %s | content_type=%s | body=%s",
                request.method,
                request.url.path,
                content_type,
                body_text[:2000] + ("...<truncated>" if len(body_text) > 2000 else ""),
            )
            raise HTTPException(status_code=422, detail="missing_gamer_id_or_reward_id")

        gamer_id = _normalize_gamer_id(gamer_id_raw)
        status = db.mark_player_reward_collected(
            gamer_id=gamer_id,
            reward_id=reward_id_raw,
        )
        if status == "not_found":
            raise HTTPException(status_code=404, detail="reward_not_found")
        if status == "wrong_owner":
            raise HTTPException(status_code=403, detail="reward_not_owned_by_gamer")
        if status == "already_collected":
            return {
                "collected": True,
                "already_collected": True,
                "reward_id": reward_id_raw,
                "gamer_id": gamer_id,
            }
        return {
            "collected": True,
            "already_collected": False,
            "reward_id": reward_id_raw,
            "gamer_id": gamer_id,
        }

    @app.post("/v1/events")
    async def ingest_event(
        request: Request,
        x_signature: str = Header(default="", alias="X-Signature"),
        x_timestamp: str = Header(default="", alias="X-Timestamp"),
    ) -> dict[str, object]:
        body = await request.body()
        if not settings.dev_disable_signature:
            if not _verify_timestamp_fresh(x_timestamp):
                raise HTTPException(status_code=401, detail="stale_or_invalid_timestamp")
            if not _verify_signature(settings.api_shared_secret, x_timestamp, body, x_signature):
                raise HTTPException(status_code=401, detail="invalid_signature")
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_json") from exc

        result = event_service.process_event(payload)
        if not bool(result.get("accepted", False)):
            raise HTTPException(status_code=400, detail=str(result.get("error", "invalid_payload")))
        if announcer is not None and not bool(result.get("already_processed", False)):
            await announcer.announce(
                event_type=str(payload.get("event_type", "")).strip().lower(),
                game_player_id=str(payload.get("player_game_id", "")).strip().upper(),
                result=result,
            )
        return result

    return app
