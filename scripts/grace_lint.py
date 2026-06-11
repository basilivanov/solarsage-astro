#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TOOL_GRACE_LINT
# ROLE: Static contract enforcer — validates Grace contract markers in Python.
# DEPENDENCIES: stdlib only (ast, pathlib, re, sys, argparse)
# GRACE_ANCHORS: [DISCOVERY, BANNER_CHECK, CONTRACT_CHECK, MAP_CHECK,
#                FUNCTION_CONTRACT_CHECK, BLOCK_PAIRING, REPORTING, CLI]
# ############################################################################
"""
Grace contract linter (Level 3 machine gate).

Per file in the active slice (default: apps/api/app), enforces:
  1. AI_HEADER banner present in the first 30 lines.
  2. Paired START_MODULE_CONTRACT / END_MODULE_CONTRACT (same id).
  3. Paired START_MODULE_MAP / END_MODULE_MAP (same id).
  4. Every public `def` / `async def` (name not starting with `_`) carries a
     START_FUNCTION_CONTRACT block immediately inside the body, declaring the
     6 mandatory fields:
         purpose, inputs, returns, side_effects, emitted_logs, error_behavior
     and closed by END_FUNCTION_CONTRACT with a matching id.
  5. All START_BLOCK / END_BLOCK markers are paired and their ids match.

Exit code 0 on success, 1 on any violation. Writes a machine-readable report
to stdout (one violation per line) and a human summary to stderr.

The linter is intentionally dependency-free so it can run in pre-commit hooks
and minimal CI containers without installing the project.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

DEFAULT_ROOTS: tuple[str, ...] = ("apps/api/app",)
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "alembic",  # generated migrations have their own conventions
        "node_modules",
        ".git",
    }
)

BANNER_SCAN_LINES = 30
BANNER_PATTERN = re.compile(r"^\s*#\s*AI_HEADER\s*:\s*\S+", re.MULTILINE)

# Generic START/END marker:  # START_<KIND>: <ID>
MARKER_RE = re.compile(
    r"^\s*#\s*(?P<edge>START|END)_(?P<kind>MODULE_CONTRACT|MODULE_MAP|"
    r"FUNCTION_CONTRACT|BLOCK)\s*:\s*(?P<id>\S+)\s*$"
)

# Inside a FUNCTION_CONTRACT block, we look for these field labels:
FUNCTION_CONTRACT_FIELDS: tuple[str, ...] = (
    "purpose",
    "inputs",
    "returns",
    "side_effects",
    "emitted_logs",
    "error_behavior",
)
FIELD_RE = re.compile(r"^\s*#\s*(?P<key>[a-z_]+)\s*:")


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------


@dataclass
class Violation:
    file: Path
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.file}:{self.line}: {self.code}: {self.message}"


@dataclass
class FileReport:
    path: Path
    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


# ----------------------------------------------------------------------------
# START_BLOCK: DISCOVERY
# ----------------------------------------------------------------------------


def iter_python_files(
    roots: Iterable[Path], exclude_dirs: frozenset[str]
) -> Iterable[Path]:
    """Yield every .py file under roots, skipping excluded directory names."""
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            yield root
            continue
        for path in root.rglob("*.py"):
            if any(part in exclude_dirs for part in path.parts):
                continue
            yield path


# END_BLOCK: DISCOVERY


# ----------------------------------------------------------------------------
# START_BLOCK: BANNER_CHECK
# ----------------------------------------------------------------------------


def check_banner(path: Path, lines: list[str], report: FileReport) -> None:
    head = "".join(lines[:BANNER_SCAN_LINES])
    if not BANNER_PATTERN.search(head):
        report.violations.append(
            Violation(
                file=path,
                line=1,
                code="GRC001",
                message=(
                    "missing AI_HEADER banner in first "
                    f"{BANNER_SCAN_LINES} lines (expected '# AI_HEADER: ...')"
                ),
            )
        )


# END_BLOCK: BANNER_CHECK


# ----------------------------------------------------------------------------
# START_BLOCK: CONTRACT_CHECK / MAP_CHECK / BLOCK_PAIRING
# ----------------------------------------------------------------------------


@dataclass
class Marker:
    edge: str  # START | END
    kind: str  # MODULE_CONTRACT | MODULE_MAP | FUNCTION_CONTRACT | BLOCK
    ident: str
    line: int


def parse_markers(lines: list[str]) -> list[Marker]:
    found: list[Marker] = []
    for idx, line in enumerate(lines, start=1):
        m = MARKER_RE.match(line)
        if not m:
            continue
        found.append(
            Marker(
                edge=m.group("edge"),
                kind=m.group("kind"),
                ident=m.group("id"),
                line=idx,
            )
        )
    return found


def check_pairing(
    path: Path,
    markers: list[Marker],
    kind: str,
    code: str,
    report: FileReport,
) -> None:
    """LIFO pairing for markers of a given kind. Reports unmatched edges."""
    stack: list[Marker] = []
    for mk in markers:
        if mk.kind != kind:
            continue
        if mk.edge == "START":
            stack.append(mk)
            continue
        # END
        if not stack:
            report.violations.append(
                Violation(
                    file=path,
                    line=mk.line,
                    code=code,
                    message=f"unmatched END_{kind}: {mk.ident}",
                )
            )
            continue
        opener = stack.pop()
        if opener.ident != mk.ident:
            report.violations.append(
                Violation(
                    file=path,
                    line=mk.line,
                    code=code,
                    message=(
                        f"END_{kind} id '{mk.ident}' does not match opener "
                        f"'{opener.ident}' at line {opener.line}"
                    ),
                )
            )
    for opener in stack:
        report.violations.append(
            Violation(
                file=path,
                line=opener.line,
                code=code,
                message=f"unclosed START_{kind}: {opener.ident}",
            )
        )


# END_BLOCK: CONTRACT_CHECK / MAP_CHECK / BLOCK_PAIRING


# ----------------------------------------------------------------------------
# START_BLOCK: FUNCTION_CONTRACT_CHECK
# ----------------------------------------------------------------------------


def _collect_public_functions(
    tree: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return every public top-level or method `def`/`async def`."""
    out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            out.append(node)
    return out


def _function_contract_block(
    func: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]
) -> tuple[int, int] | None:
    """Locate START_FUNCTION_CONTRACT / END_FUNCTION_CONTRACT inside body.

    Returns (start_line, end_line) 1-indexed, or None if not found / unclosed.
    """
    if not func.body:
        return None
    # Scan the entire function body region, including comment lines that sit
    # between the `def` signature and the first real AST statement (comments
    # are not part of the AST so they would otherwise be skipped).
    start_line = func.lineno + 1
    end_line = func.end_lineno or len(lines)
    body_slice = lines[start_line - 1 : end_line]
    open_idx: int | None = None
    open_id: str | None = None
    for offset, raw in enumerate(body_slice):
        m = MARKER_RE.match(raw)
        if not m or m.group("kind") != "FUNCTION_CONTRACT":
            continue
        if m.group("edge") == "START" and open_idx is None:
            open_idx = offset
            open_id = m.group("id")
            continue
        if m.group("edge") == "END" and open_idx is not None:
            if m.group("id") != open_id:
                return None
            return (start_line + open_idx, start_line + offset)
    return None


def check_function_contracts(
    path: Path, source: str, lines: list[str], report: FileReport
) -> None:
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report.violations.append(
            Violation(
                file=path,
                line=exc.lineno or 1,
                code="GRC000",
                message=f"syntax error: {exc.msg}",
            )
        )
        return
    for func in _collect_public_functions(tree):
        loc = _function_contract_block(func, lines)
        if loc is None:
            report.violations.append(
                Violation(
                    file=path,
                    line=func.lineno,
                    code="GRC010",
                    message=(
                        f"public function '{func.name}' is missing a paired "
                        "START_FUNCTION_CONTRACT/END_FUNCTION_CONTRACT block"
                    ),
                )
            )
            continue
        start_line, end_line = loc
        block_lines = lines[start_line:end_line - 1]
        present: set[str] = set()
        for raw in block_lines:
            stripped = raw.strip()
            if not stripped.startswith("#"):
                continue
            after = stripped.lstrip("#").strip()
            fm = re.match(r"^([a-z_]+)\s*:", after)
            if fm:
                present.add(fm.group(1))
        missing = [f for f in FUNCTION_CONTRACT_FIELDS if f not in present]
        if missing:
            report.violations.append(
                Violation(
                    file=path,
                    line=start_line,
                    code="GRC011",
                    message=(
                        f"function '{func.name}' contract is missing required "
                        f"fields: {', '.join(missing)}"
                    ),
                )
            )


# END_BLOCK: FUNCTION_CONTRACT_CHECK


def _collect_all_functions(
    tree: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return every top-level or method `def`/`async def`."""
    out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(node)
    return out


def count_python_tokens(source: str) -> int:
    import tokenize
    import io
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        ignored = {
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.COMMENT,
            tokenize.ENDMARKER,
        }
        return sum(1 for t in tokens if t.type not in ignored)
    except Exception:
        # Fallback to regex if tokenizer fails for some reason
        # Strip python comments first
        clean_source = re.sub(r'#.*', '', source)
        return len(re.findall(r'\w+|[^\w\s]', clean_source))


def check_function_sizes(
    path: Path, source: str, lines: list[str], report: FileReport
) -> None:
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return
    for func in _collect_all_functions(tree):
        start_line = func.lineno
        end_line = func.end_lineno or len(lines)
        func_source = "\n".join(lines[start_line - 1 : end_line])
        
        token_count = count_python_tokens(func_source)
        if token_count > 4000:
            report.violations.append(
                Violation(
                    file=path,
                    line=func.lineno,
                    code="GRC031",
                    message=(
                        f"function '{func.name}' too large: "
                        f"{token_count} tokens (max limit: 4000)"
                    ),
                )
            )


# ----------------------------------------------------------------------------
# START_BLOCK: REPORTING
# ----------------------------------------------------------------------------


def lint_file(path: Path) -> FileReport:
    report = FileReport(path=path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.violations.append(
            Violation(file=path, line=1, code="GRC999", message=str(exc))
        )
        return report
    lines = source.splitlines(keepends=True)

    # Empty __init__.py files are legitimately content-free namespace markers;
    # contracts would only add noise. Skip them entirely.
    if path.name == "__init__.py" and source.strip() == "":
        return report

    check_banner(path, lines, report)

    # GRC030: file too long
    if len(lines) > 1000:
        report.violations.append(
            Violation(
                file=path,
                line=1001,
                code="GRC030",
                message=f"file too long: {len(lines)} lines (max limit: 1000)",
            )
        )

    markers = parse_markers([ln.rstrip("\n") for ln in lines])
    check_pairing(path, markers, "MODULE_CONTRACT", "GRC002", report)
    check_pairing(path, markers, "MODULE_MAP", "GRC003", report)
    check_pairing(path, markers, "BLOCK", "GRC004", report)

    # Module-level contract/map presence (one of each, exactly once).
    contract_starts = [m for m in markers if m.kind == "MODULE_CONTRACT" and m.edge == "START"]
    map_starts = [m for m in markers if m.kind == "MODULE_MAP" and m.edge == "START"]
    if not contract_starts:
        report.violations.append(
            Violation(
                file=path,
                line=1,
                code="GRC020",
                message="missing START_MODULE_CONTRACT block",
            )
        )
    if not map_starts:
        report.violations.append(
            Violation(
                file=path,
                line=1,
                code="GRC021",
                message="missing START_MODULE_MAP block",
            )
        )

    check_function_contracts(path, source, [ln.rstrip("\n") for ln in lines], report)
    check_function_sizes(path, source, [ln.rstrip("\n") for ln in lines], report)
    return report


# END_BLOCK: REPORTING


# ----------------------------------------------------------------------------
# START_BLOCK: CLI
# ----------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="grace_lint",
        description="Validate Grace contract markers in Python sources.",
    )
    p.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to lint (default: apps/api/app).",
    )
    p.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Additional directory name to exclude (repeatable).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-file OK summary on success.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    roots = [Path(p) for p in (args.paths or DEFAULT_ROOTS)]
    exclude_dirs = DEFAULT_EXCLUDE_DIRS | frozenset(args.exclude_dir)

    files = sorted(set(iter_python_files(roots, exclude_dirs)))
    if not files:
        print("grace_lint: no Python files found in active slice", file=sys.stderr)
        return 0

    total_violations = 0
    for path in files:
        report = lint_file(path)
        if report.ok:
            if not args.quiet:
                print(f"OK  {path}", file=sys.stderr)
            continue
        total_violations += len(report.violations)
        for v in report.violations:
            print(v.render())  # machine-readable, stdout

    if total_violations:
        print(
            f"\ngrace_lint: FAIL — {total_violations} violation(s) "
            f"across {len(files)} file(s)",
            file=sys.stderr,
        )
        return 1
    print(f"grace_lint: PASS — {len(files)} file(s) clean", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# END_BLOCK: CLI
