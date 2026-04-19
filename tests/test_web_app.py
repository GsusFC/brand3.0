"""End-to-end web flow: /analyze → queue → /r/{token}/status → /r/{token}."""

from __future__ import annotations

import asyncio
import importlib
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team-token"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"
    os.environ["BRAND3_ANALYSIS_TIMEOUT_SECONDS"] = "30"


class WebAppFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

        # Reload the web package to pick up env.
        for mod_name in list(sys.modules):
            if mod_name.startswith("web") or mod_name == "src.config":
                importlib.reload(sys.modules[mod_name])

        from fastapi.testclient import TestClient

        from web.app import app
        from web.workers.queue import set_run_analysis_override

        self._resolver_patcher = patch(
            "web.workers.url_validator.socket.getaddrinfo",
            side_effect=lambda _h, _p: [(2, 1, 6, "", ("1.1.1.1", 0))],
        )
        self._resolver_patcher.start()

        # Override the engine entry: synthesize a fake run inserted into the DB.
        def _fake_engine(url: str) -> dict:
            with sqlite3.connect(self.db) as conn:
                cur = conn.execute(
                    "INSERT INTO brands (brand_name, url, domain, created_at, "
                    "last_seen_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                    ("Fake Brand", url, "example.com"),
                )
                brand_id = int(cur.lastrowid)
                cur = conn.execute(
                    "INSERT INTO runs (brand_id, brand_name, url, started_at, "
                    "completed_at, use_llm, use_social, composite_score) "
                    "VALUES (?, ?, ?, datetime('now'), datetime('now'), 1, 1, ?)",
                    (brand_id, "Fake Brand", url, 72.5),
                )
                run_id = int(cur.lastrowid)
                conn.execute(
                    "INSERT INTO scores (run_id, dimension_name, score, insights_json, "
                    "rules_json, created_at) "
                    "VALUES (?, 'coherencia', 70, '[]', '[]', datetime('now'))",
                    (run_id,),
                )
                conn.commit()
            return {"run_id": run_id, "composite_score": 72.5}

        set_run_analysis_override(_fake_engine)

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._resolver_patcher.stop()

        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
            "BRAND3_ANALYSIS_TIMEOUT_SECONDS",
        ):
            os.environ.pop(key, None)

    def test_analyze_rejects_invalid_url(self):
        response = self.client.post("/analyze", data={"url": "http://localhost"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("localhost", response.text)

    def test_analyze_valid_url_redirects_and_persists_row(self):
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].startswith("/r/"))
        self.assertTrue(response.headers["location"].endswith("/status"))

        token = response.headers["location"].split("/")[2]
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT * FROM web_requests WHERE token = ?", (token,)
            ).fetchone()
        self.assertIsNotNone(row)

    def test_full_flow_queued_to_ready(self):
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        token = response.headers["location"].split("/")[2]

        # Let the worker drain. The fake engine is synchronous, so one loop cycle
        # plus the worker poll interval (1s) is enough.
        for _ in range(30):
            with sqlite3.connect(self.db) as conn:
                row = conn.execute(
                    "SELECT status, run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()
            if row and row[0] == "ready":
                break
            time.sleep(0.2)

        self.assertEqual(row[0], "ready")
        self.assertIsNotNone(row[1])  # run_id populated

        # status endpoint now redirects to the report.
        status_resp = self.client.get(f"/r/{token}/status", follow_redirects=False)
        self.assertEqual(status_resp.status_code, 303)
        self.assertEqual(status_resp.headers["location"], f"/r/{token}")

        # report endpoint renders HTML.
        report_resp = self.client.get(f"/r/{token}")
        self.assertEqual(report_resp.status_code, 200)
        self.assertIn("Fake Brand", report_resp.text)

    def test_unknown_token_returns_404(self):
        response = self.client.get("/r/nope-nope/status")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
