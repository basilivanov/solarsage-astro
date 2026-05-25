from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_orchestrator_contracts.py"
SPEC = importlib.util.spec_from_file_location("check_orchestrator_contracts", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules["check_orchestrator_contracts"] = module
SPEC.loader.exec_module(module)


class FlatYamlTests(unittest.TestCase):
    def test_parse_flat_yml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.yml"
            path.write_text("version: 1\nproject_id: demo\n# ignored\n", encoding="utf-8")
            self.assertEqual(
                module.parse_flat_yml(path),
                {"version": "1", "project_id": "demo"},
            )

    def test_reject_nested_yml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.yml"
            path.write_text("project:\n  id: demo\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.parse_flat_yml(path)


class FrontmatterTests(unittest.TestCase):
    def test_extract_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet.md"
            path.write_text("---\nid: packet-x\nstatus: active\n---\n# Packet\n", encoding="utf-8")
            self.assertEqual(module.extract_frontmatter(path), {"id": "packet-x", "status": "active"})


if __name__ == "__main__":
    unittest.main()
