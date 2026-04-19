"""URL validator — accepts valid public URLs, rejects private/unsafe ones."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from web.workers.url_validator import MAX_URL_LENGTH, validate_url


def _skip_dns(func):
    """Short-circuit getaddrinfo so tests don't need network."""

    def _ok(_host, _port):
        # Pretend the host resolves to a single public IP (1.1.1.1).
        return [(2, 1, 6, "", ("1.1.1.1", 0))]

    def wrapper(*args, **kwargs):
        with patch("web.workers.url_validator.socket.getaddrinfo", side_effect=_ok):
            return func(*args, **kwargs)

    return wrapper


class UrlValidatorTests(unittest.TestCase):
    @_skip_dns
    def test_accepts_https_root(self):
        ok, value = validate_url("https://a16z.com")
        self.assertTrue(ok, value)
        self.assertEqual(value, "https://a16z.com")

    @_skip_dns
    def test_accepts_http_with_path(self):
        ok, value = validate_url("https://example.com/path/to/thing")
        self.assertTrue(ok)
        self.assertEqual(value, "https://example.com/path/to/thing")

    @_skip_dns
    def test_normalizes_host_and_trailing_slash(self):
        ok, value = validate_url("HTTPS://A16Z.COM/")
        self.assertTrue(ok)
        self.assertEqual(value, "https://a16z.com")

    def test_rejects_localhost(self):
        ok, reason = validate_url("http://localhost")
        self.assertFalse(ok)
        self.assertIn("localhost", reason)

    def test_rejects_private_ip(self):
        ok, reason = validate_url("http://192.168.1.1")
        self.assertFalse(ok)
        self.assertIn("private", reason)

    def test_rejects_ftp(self):
        ok, reason = validate_url("ftp://example.com")
        self.assertFalse(ok)
        self.assertIn("http", reason)

    def test_rejects_host_without_dot(self):
        ok, reason = validate_url("http://intranet")
        self.assertFalse(ok)
        self.assertIn("dot", reason)

    def test_rejects_over_length_url(self):
        long = "https://example.com/" + "x" * (MAX_URL_LENGTH + 1)
        ok, reason = validate_url(long)
        self.assertFalse(ok)
        self.assertIn(str(MAX_URL_LENGTH), reason)

    def test_rejects_empty(self):
        ok, _ = validate_url("   ")
        self.assertFalse(ok)

    @_skip_dns
    def test_blocklist_env_var(self):
        import os

        os.environ["BRAND3_BLOCKED_DOMAINS"] = "banned.com,evil.org"
        try:
            ok, reason = validate_url("https://banned.com/path")
            self.assertFalse(ok)
            self.assertIn("blocklist", reason)
            ok, reason = validate_url("https://sub.evil.org")
            self.assertFalse(ok)
            ok, _ = validate_url("https://ok.com")
            self.assertTrue(ok)
        finally:
            os.environ.pop("BRAND3_BLOCKED_DOMAINS", None)

    def test_rejects_loopback_ip(self):
        ok, reason = validate_url("http://127.0.0.1/foo")
        self.assertFalse(ok)
        self.assertIn("private", reason.lower() + " ")


if __name__ == "__main__":
    unittest.main()
