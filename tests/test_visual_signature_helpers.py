from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from web.visual_signature_display_data import HUMAN_REVIEW_BANNER
from web.visual_signature_display_data import HUMAN_REVIEW_GUARDRAILS
from web.visual_signature_display_data import SECTION_NAV_LABELS
from web.visual_signature_display_data import SECTION_TITLES
from web.visual_signature_display_data import visual_signature_guardrails
from web.visual_signature_display_data import visual_signature_nav
from web.visual_signature_display_data import visual_signature_next_steps
from web.visual_signature_json_data import as_list
from web.visual_signature_json_data import load_json
from web.visual_signature_json_data import nested
from web.visual_signature_json_data import pretty_json


class VisualSignatureJsonHelperTests(unittest.TestCase):
    def test_load_json_wraps_list_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

            payload = load_json(path)

        self.assertEqual(payload, {"items": [1, 2, 3]})

    def test_load_json_returns_none_for_missing_or_invalid_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertIsNone(load_json(path))
            path.write_text("{broken", encoding="utf-8")
            self.assertIsNone(load_json(path))

    def test_pretty_json_formats_stably(self):
        payload = {"b": 2, "a": 1}

        self.assertEqual(pretty_json(payload), '{\n  "a": 1,\n  "b": 2\n}')

    def test_as_list_and_nested_helpers(self):
        self.assertEqual(as_list([1, 2]), [1, 2])
        self.assertEqual(as_list("nope"), [])
        self.assertEqual(nested({"outer": {"inner": 3}}, "outer", "inner"), 3)
        self.assertIsNone(nested({"outer": "not-a-dict"}, "outer", "inner"))


class VisualSignatureDisplayHelperTests(unittest.TestCase):
    def test_navigation_labels_are_consistent(self):
        nav = visual_signature_nav("en", active_section="reviewer")
        self.assertEqual(len(nav), 5)
        self.assertEqual(nav[0]["label"], SECTION_NAV_LABELS["overview"]["en"])
        self.assertEqual(nav[-1]["label"], SECTION_NAV_LABELS["reviewer"]["en"])
        self.assertTrue(nav[-1]["active"])
        self.assertEqual(SECTION_TITLES["overview"]["es"], "Laboratorio de Visual Signature")

    def test_guardrails_and_next_steps_are_section_specific(self):
        self.assertIn("evidence-only", visual_signature_guardrails("en"))
        self.assertIn("solo evidencia", visual_signature_guardrails("es"))
        self.assertIn("Use Visual Signature pages only to inspect source artifacts and readiness.", visual_signature_next_steps("overview", "en"))
        self.assertIn("Mantén separadas las decisiones de scoring y Visual Signature.", visual_signature_next_steps("overview", "es"))
        self.assertIn("next evidence target", visual_signature_next_steps("calibration", "en")[0].lower())
        self.assertEqual(HUMAN_REVIEW_BANNER["en"]["title"], "Use visible evidence only.")
        self.assertIn("evidence-only", HUMAN_REVIEW_GUARDRAILS["en"])
