#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TOOL_GRACE_FRONT_LINT
# ROLE: Static contract enforcer for frontend — matches backend grace_lint.py.
# DEPENDENCIES: stdlib only (pathlib, re, sys, argparse)
# GRACE_ANCHORS: [DISCOVERY, BANNER_CHECK, CONTRACT_CHECK, BLOCK_PAIRING,
#                FUNCTION_SIZE_CHECK, REPORTING, CLI]
# ############################################################################
"""
Grace frontend contract linter (Level 3 machine gate).

Per file in the active frontend slice (defined in grace/frontend.paths), enforces:
  1. AI_HEADER banner present in the first 30 lines.
  2. Paired START_MODULE_CONTRACT / END_MODULE_CONTRACT (same id).
  3. Paired START_MODULE_MAP / END_MODULE_MAP (same id).
  4. All START_BLOCK / END_BLOCK markers are paired and their ids match.
  5. File too long (GRC030): max 1000 lines.
  6. Function too large (GRC031): max 4000 lexical tokens.

Exit code 0 on success, 1 on any violation. Writes a machine-readable report
to stdout (one violation per line) and a human summary to stderr.
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

BANNER_SCAN_LINES = 30
BANNER_PATTERN = re.compile(r"^\s*(?://|/\*|\*)\s*AI_HEADER\s*:\s*\S+", re.MULTILINE)


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


@dataclass
class Marker:
    edge: str  # START | END
    kind: str  # MODULE_CONTRACT | MODULE_MAP | BLOCK
    ident: str
    line: int


# ----------------------------------------------------------------------------
# START_BLOCK: DISCOVERY
# ----------------------------------------------------------------------------

def discover_frontend_files(root: Path) -> list[Path] | None:
    paths_file = root / "grace" / "frontend.paths"
    if not paths_file.exists():
        return None

    globs = []
    try:
        with open(paths_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.split("#")[0].strip()
                if line:
                    globs.append(line)
    except Exception as e:
        print(f"Error reading {paths_file}: {e}", file=sys.stderr)
        return []

    files = []
    for g in globs:
        # Resolve path patterns relative to root
        full_pattern = str(root / g)
        # Use glob.glob with recursive=True
        matched = glob.glob(full_pattern, recursive=True)
        for m in matched:
            p = Path(m)
            if p.is_file() and p.suffix in (".ts", ".tsx", ".js", ".jsx"):
                # Make relative to repo root
                try:
                    rel_p = p.relative_to(root)
                    files.append(rel_p)
                except ValueError:
                    files.append(p)

    return sorted(list(set(files)))


def expand_paths(paths: list[str], root: Path) -> list[Path]:
    files = []
    exclude_dirs = {"node_modules", ".next", ".git"}
    for p in paths:
        path_obj = Path(p)
        if not path_obj.is_absolute():
            resolved = path_obj.resolve()
            if not resolved.exists():
                resolved = (root / path_obj).resolve()
        else:
            resolved = path_obj.resolve()

        if resolved.is_file():
            if resolved.suffix in (".ts", ".tsx", ".js", ".jsx"):
                try:
                    files.append(resolved.relative_to(root))
                except ValueError:
                    files.append(resolved)
        elif resolved.is_dir():
            for sub_p in resolved.rglob("*"):
                try:
                    rel_to_root = sub_p.relative_to(root)
                    if any(part in exclude_dirs for part in rel_to_root.parts):
                        continue
                    if sub_p.is_file() and sub_p.suffix in (".ts", ".tsx", ".js", ".jsx"):
                        files.append(rel_to_root)
                except ValueError:
                    if sub_p.is_file() and sub_p.suffix in (".ts", ".tsx", ".js", ".jsx"):
                        files.append(sub_p)
        else:
            try:
                files.append(path_obj.relative_to(root))
            except ValueError:
                files.append(path_obj)
    return sorted(list(set(files)))

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
                    f"{BANNER_SCAN_LINES} lines (expected '// AI_HEADER: ...' or similar)"
                ),
            )
        )

# END_BLOCK: BANNER_CHECK


# ----------------------------------------------------------------------------
# START_BLOCK: CONTRACT_CHECK / MAP_CHECK / BLOCK_PAIRING
# ----------------------------------------------------------------------------

def parse_markers(lines: list[str]) -> list[Marker]:
    found: list[Marker] = []
    pattern = re.compile(
        r"(?://|/\*|\*)\s*(?P<edge>START|END)_(?P<kind>MODULE_CONTRACT|MODULE_MAP|BLOCK)\s*:\s*(?P<id>[^\s\*\/]+)"
    )
    for idx, line in enumerate(lines, start=1):
        m = pattern.search(line)
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
    starts = [m for m in markers if m.kind == kind and m.edge == "START"]
    ends = [m for m in markers if m.kind == kind and m.edge == "END"]

    if kind in ("MODULE_CONTRACT", "MODULE_MAP"):
        if not starts or not ends:
            report.violations.append(
                Violation(
                    file=path,
                    line=1,
                    code=code,
                    message=f"START_{kind}/END_{kind} mismatch (starts={len(starts)}, ends={len(ends)})",
                )
            )
            return

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
# START_BLOCK: FUNCTION_SIZE_CHECK
# ----------------------------------------------------------------------------

def scan_js_tokens(source: str) -> list[tuple[str, str, int]]:
    token_specification = [
        ('COMMENT_SINGLE', r'//.*'),
        ('COMMENT_MULTI', r'/\*[\s\S]*?\*/'),
        ('STRING_DOUBLE', r'"(?:[^"\\]|\\.)*"'),
        ('STRING_SINGLE', r"'(?:[^'\\]|\\.)*'"),
        ('STRING_TEMPLATE', r'`(?:[^`\\]|\\.)*`'),
        ('BRACE_OPEN', r'\{'),
        ('BRACE_CLOSE', r'\}'),
        ('WORD', r'[a-zA-Z_0-9]+'),
        ('OTHER', r'[^\s\w\{\}\'\"]+'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t\r]+'),
    ]
    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
    
    tokens = []
    line_num = 1
    for mo in re.finditer(tok_regex, source):
        kind = mo.lastgroup
        value = mo.group(kind)
        if kind == 'NEWLINE':
            line_num += 1
        elif kind == 'SKIP':
            pass
        else:
            tokens.append((kind, value, line_num))
            line_num += value.count('\n')
    return tokens


def check_function_sizes(path: Path, source: str, report: FileReport) -> None:
    tokens = scan_js_tokens(source)
    functions = []
    open_functions = []
    brace_depth = 0
    last_boundary_idx = 0

    for idx, (kind, value, line) in enumerate(tokens):
        if kind == 'BRACE_OPEN':
            window = tokens[last_boundary_idx:idx]
            is_func = False
            func_name = 'anonymous'
            func_keyword_idx = -1
            for w_idx, (w_kind, w_val, w_line) in enumerate(window):
                if w_kind == 'WORD' and w_val == 'function':
                    is_func = True
                    func_keyword_idx = w_idx
                    break
            arrow_idx = -1
            for w_idx, (w_kind, w_val, w_line) in enumerate(window):
                if w_kind == 'OTHER' and w_val == '=>':
                    is_func = True
                    arrow_idx = w_idx
                    break
            if is_func:
                if func_keyword_idx != -1:
                    for w_idx in range(func_keyword_idx + 1, len(window)):
                        w_kind, w_val, _ = window[w_idx]
                        if w_kind == 'WORD':
                            if w_val not in ('default', 'export'):
                                func_name = w_val
                                break
                elif arrow_idx != -1:
                    eq_idx = -1
                    for w_idx in range(arrow_idx - 1, -1, -1):
                        w_kind, w_val, _ = window[w_idx]
                        if w_kind == 'OTHER' and '=' in w_val:
                            eq_idx = w_idx
                            break
                    if eq_idx != -1:
                        for w_idx in range(eq_idx - 1, -1, -1):
                            w_kind, w_val, _ = window[w_idx]
                            if w_kind == 'WORD' and w_val not in ('const', 'let', 'var', 'export'):
                                func_name = w_val
                                break
                start_token_idx = last_boundary_idx
                for w_idx, (w_kind, w_val, _) in enumerate(window):
                    if w_kind == 'WORD' and w_val in ('const', 'let', 'var', 'export', 'function'):
                        start_token_idx = last_boundary_idx + w_idx
                        break
                open_functions.append({
                    'name': func_name,
                    'start_token_idx': start_token_idx,
                    'start_depth': brace_depth,
                    'start_line': tokens[start_token_idx][2]
                })
            brace_depth += 1
            last_boundary_idx = idx + 1
        elif kind == 'BRACE_CLOSE':
            brace_depth -= 1
            if open_functions and open_functions[-1]['start_depth'] == brace_depth:
                fn = open_functions.pop()
                lexical_tokens_count = 0
                for tok_idx in range(fn['start_token_idx'], idx + 1):
                    t_kind, _, _ = tokens[tok_idx]
                    if t_kind not in ('COMMENT_SINGLE', 'COMMENT_MULTI', 'SKIP', 'NEWLINE'):
                        lexical_tokens_count += 1
                functions.append({
                    'name': fn['name'],
                    'start_line': fn['start_line'],
                    'token_count': lexical_tokens_count
                })
            last_boundary_idx = idx + 1
        elif kind == 'OTHER' and ';' in value:
            last_boundary_idx = idx + 1

    for fn in functions:
        if fn['token_count'] > 4000:
            report.violations.append(
                Violation(
                    file=path,
                    line=fn['start_line'],
                    code="GRC031",
                    message=(
                        f"function '{fn['name']}' too large: "
                        f"{fn['token_count']} tokens (max limit: 4000)"
                    ),
                )
            )

# END_BLOCK: FUNCTION_SIZE_CHECK


# ----------------------------------------------------------------------------
# START_BLOCK: REPORTING
# ----------------------------------------------------------------------------

def lint_file(path: Path, root: Path) -> FileReport:
    report = FileReport(path=path)
    full_path = root / path
    try:
        source = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.violations.append(
            Violation(file=path, line=1, code="GRC999", message=str(exc))
        )
        return report

    lines = source.splitlines(keepends=True)

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

    check_function_sizes(path, source, report)

    return report

# END_BLOCK: REPORTING


# ----------------------------------------------------------------------------
# START_BLOCK: CLI
# ----------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="grace_front_lint",
        description="Validate Grace contract markers in Frontend sources.",
    )
    p.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to lint (default: defined in grace/frontend.paths).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-file OK summary on success.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    
    # Locate repo root (assumed to be parent of scripts/ directory)
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent

    if args.paths:
        files = expand_paths(args.paths, root)
    else:
        files = discover_frontend_files(root)
        if files is None:
            print("grace_front_lint: FAIL — GRC900: missing frontend paths file", file=sys.stderr)
            return 1

    if not files:
        print("grace_front_lint: FAIL — GRC901: no frontend files matched active frontend slice", file=sys.stderr)
        return 1

    total_violations = 0
    for rel_path in files:
        report = lint_file(rel_path, root)
        if report.ok:
            if not args.quiet:
                print(f"OK  {rel_path}", file=sys.stderr)
            continue
        total_violations += len(report.violations)
        for v in report.violations:
            print(v.render())  # machine-readable, stdout

    if total_violations:
        print(
            f"\ngrace_front_lint: FAIL — {total_violations} violation(s) "
            f"across {len(files)} file(s)",
            file=sys.stderr,
        )
        return 1
    print(f"grace_front_lint: PASS — {len(files)} file(s) clean", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# END_BLOCK: CLI
