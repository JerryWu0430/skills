#!/usr/bin/env python3
"""Thin routers: no service logic in HTTP routers (FastAPI + SQLAlchemy).

A router parses the request, resolves auth, calls ONE service function and returns the
schema. Everything else is service logic. Machine proxies, per router module:

  db-access      a Session call other than commit / rollback / refresh (query, add, delete,
                 flush, execute, get, ...): building a query or staging a write is service
                 work; the router only closes the transaction around it.
  orm-import     importing sqlalchemy (bar sqlalchemy.orm.Session) or anything from the
                 project's database module but its session dependency (the engine, ...).
  long-function  a function body over --max-lines lines, docstring excluded.

Legacy violations are COUNTED per file + rule in a JSON baseline that only shrinks: a new
violation fails, and a fixed one fails until the baseline is lowered with --write.

  python check_thin_routers.py --routers app/routers --baseline scripts/thin-routers-baseline.json
  ... --write    record today's debt (first run) or ratchet the baseline down
  ... --report   list every violation, exit 0 (survey a repo with no baseline yet)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

SESSION_CALLS_ALLOWED = {"commit", "rollback", "refresh"}


def _body_lines(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    return body[-1].end_lineno - body[0].lineno + 1 if body else 0


def _session_names(tree: ast.Module, session_dep: str) -> set[str]:
    names = {"db"}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = fn.args.posonlyargs + fn.args.args
            defaults = [None] * (len(positional) - len(fn.args.defaults)) + fn.args.defaults
            pairs = list(zip(positional, defaults)) + list(zip(fn.args.kwonlyargs, fn.args.kw_defaults))
            for arg, default in pairs:
                annotation = ast.unparse(arg.annotation) if arg.annotation else ""
                if annotation.endswith("Session") or (
                    default is not None and ast.unparse(default) == f"Depends({session_dep})"
                ):
                    names.add(arg.arg)
    return names


def violations(path: Path, args: argparse.Namespace) -> list[tuple[str, int, str]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    sessions = _session_names(tree, args.session_dep)
    allowed_imports = {("sqlalchemy.orm", "Session"), (args.database_module, args.session_dep)}
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in sessions
            and node.func.attr not in SESSION_CALLS_ALLOWED
        ):
            found.append(("db-access", node.lineno, f"{node.func.value.id}.{node.func.attr}()"))
        elif isinstance(node, ast.Import):
            found += [("orm-import", node.lineno, a.name) for a in node.names if a.name.split(".")[0] == "sqlalchemy"]
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")
            # `from ..database import x` / `from app.database import x` both end in the module name.
            key = "sqlalchemy" if module[0] == "sqlalchemy" else module[-1]
            if key in {"sqlalchemy", args.database_module}:
                dotted = node.module if key == "sqlalchemy" else key
                found += [
                    ("orm-import", node.lineno, f"{dotted}.{a.name}")
                    for a in node.names
                    if (dotted, a.name) not in allowed_imports
                ]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines = _body_lines(node)
            if lines > args.max_lines:
                found.append(("long-function", node.lineno, f"{node.name}: {lines} lines > {args.max_lines}"))
    return sorted(found, key=lambda v: v[1])


def _total(counts: dict[str, dict[str, int]]) -> int:
    return sum(sum(rules.values()) for rules in counts.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--routers", type=Path, default=Path("app/routers"))
    parser.add_argument("--baseline", type=Path, default=Path("scripts/thin-routers-baseline.json"))
    parser.add_argument("--max-lines", type=int, default=30)
    parser.add_argument("--database-module", default="database", help="module holding the engine + session dep")
    parser.add_argument("--session-dep", default="get_db", help="the request-session dependency function")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    baseline: dict[str, dict[str, int]] = json.loads(args.baseline.read_text()) if args.baseline.exists() else {}
    counts: dict[str, dict[str, int]] = {}
    failures, report = [], []
    for path in sorted(args.routers.rglob("*.py")):
        file = path.as_posix()
        by_rule: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for rule, line, detail in violations(path, args):
            by_rule[rule].append((line, detail))
            report.append(f"{file}:{line}  {rule}  {detail}")
        for rule, hits in sorted(by_rule.items()):
            allowed = baseline.get(file, {}).get(rule, 0)
            if len(hits) > allowed:
                listed = "\n".join(f"    {file}:{line}  {detail}" for line, detail in hits)
                failures.append(f"{file}: {len(hits)} {rule} (baseline {allowed}). Move it into services.\n{listed}")
            counts.setdefault(file, {})[rule] = len(hits)

    if args.report:
        print("\n".join(report) or "No violations.")
        print(f"\n{len(report)} violations in {len(counts)} router files.")
        return 0
    if args.write and not args.baseline.exists():
        failures = []  # bootstrap: record today's debt once; from then on it only shrinks
    if failures:
        print("Service logic in routers:\n", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    if args.write:
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n")
        print(f"{args.baseline}: {_total(counts)} violations in {len(counts)} files recorded.")
        return 0
    if counts != baseline:
        print(f"Stale baseline (lower it: rerun with --write)", file=sys.stderr)
        return 1
    print(f"Thin routers OK ({_total(counts)} legacy violations in {len(counts)} files on the shrink-only list).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
