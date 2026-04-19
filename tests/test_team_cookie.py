"""Signed cookie behaviour: valid, tampered, and expired variants."""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock

from itsdangerous import URLSafeTimedSerializer

from web.middleware.team_cookie import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    create_serializer,
    is_team_request,
    set_team_cookie,
)


def _make_request(cookies: dict[str, str]) -> MagicMock:
    req = MagicMock()
    req.cookies = cookies
    return req


class TeamCookieTests(unittest.TestCase):
    SECRET = "test-secret-" + "x" * 40

    def test_set_cookie_writes_expected_name_and_attrs(self):
        response = MagicMock()
        serializer = create_serializer(self.SECRET)
        set_team_cookie(response, serializer)
        response.set_cookie.assert_called_once()
        kwargs = response.set_cookie.call_args.kwargs
        args = response.set_cookie.call_args.args
        self.assertEqual(args[0], COOKIE_NAME)
        self.assertEqual(kwargs.get("max_age"), COOKIE_MAX_AGE)
        self.assertTrue(kwargs.get("httponly"))
        self.assertEqual(kwargs.get("samesite"), "lax")

    def test_valid_cookie_is_recognised(self):
        serializer = create_serializer(self.SECRET)
        token = serializer.dumps({"unlocked_at": int(time.time())})
        self.assertTrue(is_team_request(_make_request({COOKIE_NAME: token}), serializer))

    def test_wrong_secret_fails(self):
        serializer_a = create_serializer(self.SECRET)
        serializer_b = create_serializer("a-different-" + "y" * 40)
        token = serializer_a.dumps({"unlocked_at": int(time.time())})
        self.assertFalse(is_team_request(_make_request({COOKIE_NAME: token}), serializer_b))

    def test_tampered_cookie_fails(self):
        serializer = create_serializer(self.SECRET)
        token = serializer.dumps({"unlocked_at": int(time.time())}) + "garbage"
        self.assertFalse(is_team_request(_make_request({COOKIE_NAME: token}), serializer))

    def test_expired_cookie_fails(self):
        # Force expiry by temporarily shrinking COOKIE_MAX_AGE and sleeping past it.
        import web.middleware.team_cookie as mod

        original = mod.COOKIE_MAX_AGE
        mod.COOKIE_MAX_AGE = 1
        try:
            serializer = create_serializer(self.SECRET)
            token = serializer.dumps({"unlocked_at": int(time.time())})
            time.sleep(2)
            self.assertFalse(is_team_request(_make_request({COOKIE_NAME: token}), serializer))
        finally:
            mod.COOKIE_MAX_AGE = original

    def test_no_cookie_returns_false(self):
        self.assertFalse(is_team_request(_make_request({}), create_serializer(self.SECRET)))


if __name__ == "__main__":
    unittest.main()
