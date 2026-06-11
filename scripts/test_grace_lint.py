# ############################################################################
# AI_HEADER: TOOL_GRACE_LINT_TESTS
# ROLE: Self-tests for scripts/grace_lint.py — guards the gatekeeper itself.
# DEPENDENCIES: stdlib (unittest, tempfile, pathlib, importlib)
# GRACE_ANCHORS: [FIXTURES, BANNER_TESTS, PAIRING_TESTS, FUNCTION_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: T-GRACE-LINT
# purpose: Pin grace_lint.py behaviour so future edits to the linter cannot
#   silently weaken any of the five Level-3 invariants.
# owns:
#   - scripts/test_grace_lint.py
# inputs: none (self-contained fixtures via tempfile)
# outputs: unittest results (exit 0 = green)
# dependencies: scripts/grace_lint.py
# side_effects: creates and cleans up a temporary directory per test
# invariants:
#   - a clean, fully-contracted file is reported OK
#   - each violation class (banner, contract, map, function-contract, block)
#     produces exactly one matching violation code on a minimal failing fixture
# failure_policy: any failing case fails CI
# non_goals: does not test ruff/mypy/pytest integration
# END_MODULE_CONTRACT: T-GRACE-LINT

# START_MODULE_MAP: T-GRACE-LINT
# public_entrypoints: []
# semantic_blocks:
#   - FIXTURES: clean and broken source builders
#   - BANNER_TESTS: GRC001 coverage
#   - PAIRING_TESTS: GRC002/003/004/020/021 coverage
#   - FUNCTION_TESTS: GRC010/011 coverage
# owned_tests: self
# END_MODULE_MAP: T-GRACE-LINT

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "grace_lint", _HERE / "grace_lint.py"
)
assert _SPEC and _SPEC.loader
grace_lint = importlib.util.module_from_spec(_SPEC)
sys.modules["grace_lint"] = grace_lint
_SPEC.loader.exec_module(grace_lint)


# START_BLOCK: FIXTURES
CLEAN_SOURCE = '''\
# ############################################################################
# AI_HEADER: TEST_FIXTURE
# ############################################################################

# START_MODULE_CONTRACT: T-FIX
# purpose: x
# END_MODULE_CONTRACT: T-FIX

# START_MODULE_MAP: T-FIX
# public_entrypoints: []
# END_MODULE_MAP: T-FIX


def do_thing() -> int:
    # START_FUNCTION_CONTRACT: T-FIX.do_thing
    # purpose: return 1
    # inputs: none
    # returns: int
    # side_effects: none
    # emitted_logs: none
    # error_behavior: none
    # END_FUNCTION_CONTRACT: T-FIX.do_thing

    # START_BLOCK: BODY
    return 1
    # END_BLOCK: BODY
'''


def _lint(source: str) -> list[str]:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sample.py"
        p.write_text(source, encoding="utf-8")
        report = grace_lint.lint_file(p)
        return [v.code for v in report.violations]
# END_BLOCK: FIXTURES


# START_BLOCK: BANNER_TESTS
class BannerTests(unittest.TestCase):
    def test_clean_source_has_no_violations(self) -> None:
        self.assertEqual(_lint(CLEAN_SOURCE), [])

    def test_missing_banner_reports_grc001(self) -> None:
        broken = CLEAN_SOURCE.replace("# AI_HEADER: TEST_FIXTURE", "# nope")
        self.assertIn("GRC001", _lint(broken))
# END_BLOCK: BANNER_TESTS


# START_BLOCK: PAIRING_TESTS
class PairingTests(unittest.TestCase):
    def test_unclosed_module_contract(self) -> None:
        broken = CLEAN_SOURCE.replace("# END_MODULE_CONTRACT: T-FIX\n", "")
        self.assertIn("GRC002", _lint(broken))

    def test_unclosed_module_map(self) -> None:
        broken = CLEAN_SOURCE.replace("# END_MODULE_MAP: T-FIX\n", "")
        self.assertIn("GRC003", _lint(broken))

    def test_unclosed_block(self) -> None:
        broken = CLEAN_SOURCE.replace("    # END_BLOCK: BODY\n", "")
        self.assertIn("GRC004", _lint(broken))

    def test_missing_module_contract_block(self) -> None:
        broken = CLEAN_SOURCE.replace(
            "# START_MODULE_CONTRACT: T-FIX\n# purpose: x\n# END_MODULE_CONTRACT: T-FIX\n",
            "",
        )
        self.assertIn("GRC020", _lint(broken))
# END_BLOCK: PAIRING_TESTS


# START_BLOCK: FUNCTION_TESTS
class FunctionContractTests(unittest.TestCase):
    def test_missing_function_contract(self) -> None:
        broken = CLEAN_SOURCE.replace(
            "    # START_FUNCTION_CONTRACT: T-FIX.do_thing\n",
            "",
        ).replace(
            "    # END_FUNCTION_CONTRACT: T-FIX.do_thing\n",
            "",
        )
        self.assertIn("GRC010", _lint(broken))

    def test_missing_required_field(self) -> None:
        broken = CLEAN_SOURCE.replace("    # error_behavior: none\n", "")
        self.assertIn("GRC011", _lint(broken))

    def test_private_function_is_exempt(self) -> None:
        src = CLEAN_SOURCE.replace("def do_thing", "def _do_thing")
        # Remove the function contract too — private fns should not need it.
        for line in (
            "    # START_FUNCTION_CONTRACT: T-FIX.do_thing\n",
            "    # purpose: return 1\n",
            "    # inputs: none\n",
            "    # returns: int\n",
            "    # side_effects: none\n",
            "    # emitted_logs: none\n",
            "    # error_behavior: none\n",
            "    # END_FUNCTION_CONTRACT: T-FIX.do_thing\n",
        ):
            src = src.replace(line, "")
        self.assertEqual(_lint(src), [])
# END_BLOCK: FUNCTION_TESTS


class SizeTests(unittest.TestCase):
    def test_file_1000_lines_passes(self) -> None:
        # Construct a clean file and pad it to exactly 1000 lines
        lines = CLEAN_SOURCE.splitlines()
        padding = 1000 - len(lines)
        src = CLEAN_SOURCE + "\n" * padding
        self.assertEqual(len(src.splitlines()), 1000)
        self.assertEqual(_lint(src), [])

    def test_file_1001_lines_fails_grc030(self) -> None:
        lines = CLEAN_SOURCE.splitlines()
        padding = 1001 - len(lines)
        src = CLEAN_SOURCE + "\n" * padding
        self.assertEqual(len(src.splitlines()), 1001)
        self.assertIn("GRC030", _lint(src))

    def test_function_normal_passes(self) -> None:
        # CLEAN_SOURCE has a normal-sized function
        self.assertEqual(_lint(CLEAN_SOURCE), [])

    def test_function_oversized_fails_grc031(self) -> None:
        # Create a function body with > 4000 tokens
        # Each "    x = 1\n" has 3 tokens (x, =, 1)
        # 1500 * 3 = 4500 tokens
        lines = CLEAN_SOURCE.splitlines()
        # insert before the block body
        insert_idx = lines.index("    # START_BLOCK: BODY")
        lines.insert(insert_idx, "    x = 1\n" * 1500)
        src = "\n".join(lines)
        self.assertIn("GRC031", _lint(src))


if __name__ == "__main__":
    unittest.main()
