import importlib.util
import unittest
from unittest.mock import patch


FASTAPI_AVAILABLE = bool(importlib.util.find_spec("fastapi")) and bool(importlib.util.find_spec("starlette"))


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed")
class ApiTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_runs_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"id": 1, "brand_name": "Example"}]
        with patch("src.api.app.brand_service.list_runs", return_value=expected):
            response = client.get("/api/runs", params={"brand_name": "Example", "limit": 5})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_brands_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"brand_name": "Stripe", "brand_profile": {"domain": "stripe.com"}}]
        with patch("src.api.app.brand_service.list_brands", return_value=expected):
            response = client.get("/api/brands", params={"limit": 10})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_profiles_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"profile_id": "base", "label": "Base"}]
        with patch("src.api.app.brand_service.list_profiles", return_value=expected):
            response = client.get("/api/profiles")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)


if __name__ == "__main__":
    unittest.main()
