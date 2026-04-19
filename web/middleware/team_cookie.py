"""Signed cookie that bypasses the per-IP rate limit for the FLOC team."""

from __future__ import annotations

import time

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "brand3_team"
COOKIE_MAX_AGE = 90 * 24 * 3600  # 90 days


def create_serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="brand3-team-cookie")


def set_team_cookie(response: Response, serializer: URLSafeTimedSerializer) -> None:
    payload = {"unlocked_at": int(time.time())}
    token = serializer.dumps(payload)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def is_team_request(request: Request, serializer: URLSafeTimedSerializer) -> bool:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return False
    try:
        serializer.loads(raw, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return True
