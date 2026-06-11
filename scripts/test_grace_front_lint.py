# ############################################################################
# AI_HEADER: TOOL_GRACE_FRONT_LINT_TESTS
# ROLE: Self-tests for scripts/grace_front_lint.py — guards the frontend linter.
# DEPENDENCIES: stdlib (unittest, tempfile, pathlib, importlib)
# ############################################################################
"""
Self-tests for scripts/grace_front_lint.py.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "grace_front_lint", _HERE / "grace_front_lint.py"
)
assert _SPEC and _SPEC.loader
grace_front_lint = importlib.util.module_from_spec(_SPEC)
sys.modules["grace_front_lint"] = grace_front_lint
_SPEC.loader.exec_module(grace_front_lint)

# Clean mock frontend source
CLEAN_FRONT_SOURCE = """// ############################################################################
// AI_HEADER: TEST_FIXTURE
// ############################################################################

// START_MODULE_CONTRACT: M-FIX
// purpose: test
// END_MODULE_CONTRACT: M-FIX

// START_MODULE_MAP: M-FIX
// public_entrypoints: []
// END_MODULE_MAP: M-FIX

export function normalFunction() {
  // START_BLOCK: BODY
  return 123;
  // END_BLOCK: BODY
}
"""

class FrontendLintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        # Create a mock grace directory
        (self.root / "grace").mkdir()
        self.paths_file = self.root / "grace" / "frontend.paths"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write_paths(self, lines: list[str]) -> None:
        self.paths_file.write_text("\n".join(lines), encoding="utf-8")

    def _write_file(self, rel_path: str, content: str) -> Path:
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _run_lint(self, args: list[str] = []) -> tuple[int, list[str]]:
        # Run main() but redirect stdout/stderr and intercept exit codes
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = tempfile.TemporaryFile(mode="w+")
        sys.stderr = tempfile.TemporaryFile(mode="w+")
        
        # Save original functions to restore later
        orig_discover = grace_front_lint.discover_frontend_files
        orig_expand = grace_front_lint.expand_paths
        
        try:
            # Mock discover_frontend_files to use our temp root
            grace_front_lint.discover_frontend_files = lambda r: orig_discover(self.root)
            
            # Mock expand_paths to resolve relative to temp root
            grace_front_lint.expand_paths = lambda paths, r: orig_expand(paths, self.root)
            
            def mock_main(argv=None):
                args = grace_front_lint._parse_args(argv or [])
                if args.paths:
                    files = grace_front_lint.expand_paths(args.paths, self.root)
                else:
                    files = grace_front_lint.discover_frontend_files(self.root)
                    if files is None:
                        print("grace_front_lint: FAIL — GRC900", file=sys.stderr)
                        return 1
                if not files:
                    print("grace_front_lint: FAIL — GRC901", file=sys.stderr)
                    return 1
                
                total = 0
                for f in files:
                    report = grace_front_lint.lint_file(f, self.root)
                    total += len(report.violations)
                    for v in report.violations:
                        print(v.render())
                return 1 if total > 0 else 0

            code = mock_main(args)
            
            sys.stdout.seek(0)
            sys.stderr.seek(0)
            stdout_content = sys.stdout.read()
            stderr_content = sys.stderr.read()
            
            violations = []
            for line in stdout_content.splitlines():
                parts = line.split(": ")
                if len(parts) >= 3:
                    violations.append(parts[1]) # violation code e.g. GRC001
                    
            return code, violations
        finally:
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Restore original functions to avoid recursion on subsequent runs
            grace_front_lint.discover_frontend_files = orig_discover
            grace_front_lint.expand_paths = orig_expand

    def test_clean_file_passes(self) -> None:
        self._write_paths(["app/page.tsx"])
        self._write_file("app/page.tsx", CLEAN_FRONT_SOURCE)
        code, violations = self._run_lint()
        self.assertEqual(code, 0)
        self.assertEqual(violations, [])

    def test_missing_banner_reports_grc001(self) -> None:
        self._write_paths(["app/page.tsx"])
        broken = CLEAN_FRONT_SOURCE.replace("AI_HEADER:", "NOPE:")
        self._write_file("app/page.tsx", broken)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC001", violations)

    def test_missing_end_module_contract_reports_grc002(self) -> None:
        self._write_paths(["app/page.tsx"])
        broken = CLEAN_FRONT_SOURCE.replace("END_MODULE_CONTRACT: M-FIX", "")
        self._write_file("app/page.tsx", broken)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC002", violations)

    def test_missing_end_module_map_reports_grc003(self) -> None:
        self._write_paths(["app/page.tsx"])
        broken = CLEAN_FRONT_SOURCE.replace("END_MODULE_MAP: M-FIX", "")
        self._write_file("app/page.tsx", broken)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC003", violations)

    def test_missing_end_block_reports_grc004(self) -> None:
        self._write_paths(["app/page.tsx"])
        broken = CLEAN_FRONT_SOURCE.replace("END_BLOCK: BODY", "")
        self._write_file("app/page.tsx", broken)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC004", violations)

    def test_file_1000_lines_passes(self) -> None:
        self._write_paths(["app/page.tsx"])
        lines = CLEAN_FRONT_SOURCE.splitlines()
        padding = 1000 - len(lines)
        src = CLEAN_FRONT_SOURCE + "\n" * padding
        self._write_file("app/page.tsx", src)
        code, violations = self._run_lint()
        self.assertEqual(code, 0)
        self.assertEqual(violations, [])

    def test_file_1001_lines_fails_grc030(self) -> None:
        self._write_paths(["app/page.tsx"])
        lines = CLEAN_FRONT_SOURCE.splitlines()
        padding = 1001 - len(lines)
        src = CLEAN_FRONT_SOURCE + "\n" * padding
        self._write_file("app/page.tsx", src)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC030", violations)

    def test_normal_arrow_component_passes(self) -> None:
        self._write_paths(["app/page.tsx"])
        src = CLEAN_FRONT_SOURCE + "\nconst Small = () => { return 1; }"
        self._write_file("app/page.tsx", src)
        code, violations = self._run_lint()
        self.assertEqual(code, 0)
        self.assertEqual(violations, [])

    def test_oversized_arrow_component_fails_grc031(self) -> None:
        self._write_paths(["app/page.tsx"])
        # Construct large arrow function
        # 1500 lines of `let x = 1;`
        large_body = "\n".join("  let x = 1;" for _ in range(1500))
        src = CLEAN_FRONT_SOURCE + f"\nconst Large = () => {{\n{large_body}\n}}"
        self._write_file("app/page.tsx", src)
        code, violations = self._run_lint()
        self.assertEqual(code, 1)
        self.assertIn("GRC031", violations)

    def test_missing_frontend_paths_fails(self) -> None:
        # Delete the paths file if it exists
        if self.paths_file.exists():
            self.paths_file.unlink()
        code, _ = self._run_lint()
        self.assertEqual(code, 1)

    def test_empty_frontend_paths_fails(self) -> None:
        # Create empty paths file
        self._write_paths([])
        code, _ = self._run_lint()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
