---
name: thin-routers
description: Enforce "no service logic in routers" on the current branch of a FastAPI + SQLAlchemy backend. Use before opening or updating a PR that touches the routers, when a thin-routers CI check fails, or when asked to check, review or fix router thinness, or to move logic out of a router into the service layer. Runs the bundled AST check (or the repo's own copy), reviews the branch diff for logic a script can't see, and says (or does) where each piece moves. Can also install the check + shrink-only baseline into a repo.
---

# Thin routers

A router handler parses the request, resolves auth through a dependency, calls ONE service
function and returns the response schema. Everything else is service logic and lives in the
service layer.

Report first. Apply moves only when the user asked for a fix (or invoked `/thin-routers fix`).

## 0. Find the project's setup

- The repo ships its own `.claude/skills/thin-routers/SKILL.md`: read it and follow it instead
  of this file (it carries the project's paths and domain map; a personal skill of the same
  name shadows it, so it may not have been loaded).
- Routers dir (`app/routers`, `backend/app/routers`, ...) and services dir.
- The repo's own check: `git ls-files | grep check_thin_routers`. If it exists, use it and its
  baseline: they are the source of truth (CI runs them).
- Project rules: read `CLAUDE.md` / architecture docs for the service domain map, the
  tenant-scoped loader helper, the auth dependency ladder and the commit convention.

No repo check yet: run the bundled one in survey mode and offer to install it (step 7).

```bash
python <this skill>/scripts/check_thin_routers.py --routers <routers dir> --report
```

## 1. Scope the branch

```bash
BASE=$(git merge-base origin/main HEAD)
git diff --name-only "$BASE" -- <routers dir>   # committed + uncommitted router changes
```

## 2. Machine check (blocking where installed)

Run the repo's check (`--write` lowers the baseline after logic leaves a router; never raise it
by hand). Rules:

- `db-access`: any Session call but `commit` / `rollback` / `refresh` (query, add, delete,
  flush, execute, get, ...). Building a query or staging a write is service work.
- `orm-import`: `sqlalchemy` other than `sqlalchemy.orm.Session`; the database module other
  than the session dependency (no engine, no `SessionLocal`).
- `long-function`: function body over 30 lines, docstring excluded.

Counts are per file + rule, so a new hit can be any line in that file's list: find it in the diff.

## 3. Review the diff (what the script can't see)

Read `git diff "$BASE" -- <routers dir>` and every router function it touches. Flag:

- **Business rules written without the session**: status transitions, money / stock / unit
  arithmetic, cost or margin math, matching / dedupe, branching on domain state, loops that
  build or aggregate data.
- **ORM mutation in the handler**: `setattr(obj, ...)`, `obj.field = ...` beyond echoing one
  request field. Applying an update payload is service work.
- **Router-level helpers** that are not a pure ORM → schema mapper used only in that file.
- **Inline role checks**: an access tier belongs in an auth dependency; a visibility rule
  repeated across files belongs in one named helper.
- **Hand-rolled tenant loads** where the project has a scoped loader.
- **Duplicates**: grep the services for an existing function before proposing a new one.
- **A handler calling another handler**: extract the shared piece into the service.

Allowed in a router: auth dependencies, request parsing (`Query` / `Body` / `UploadFile`),
the scoped loader, commit/refresh/rollback around a commit-free service, analytics events after
the commit, `Response` / header building, `BackgroundTasks` injection, endpoint docstrings.

## 4. Where it goes

The project's domain package for the concept. Prefer an existing module; create a sibling when
the target would pass the repo's file-size budget. Services may raise HTTP errors and use the
scoped loader. Follow the area's commit habit: commit-free services (router commits) where a
multi-step write must be one transaction.

## 5. Moving it (only when fixing)

A move changes structure, never behaviour:

- Keep every error `detail` and status code exact; tests assert them.
- Keep audit / ticket comments with the code they explain.
- Repoint tests that import or monkeypatch the router symbol (`grep -rn "routers.<module>" tests/`).
- A bug found while moving: its own commit (or PR) with a regression test, or noted in the PR
  body. Don't fix it silently inside the move commit.
- Schema classes keep their names (generated clients key on them); regenerate the client if
  the repo has one.

Verify: lint, import-layer check, the thin-routers check with `--write` then without, the
touched test suites.

## 6. Report

```
Thin routers: <PASS | FAIL>  (<n> legacy violations, baseline <lowered by k | unchanged>)

Blocking (script)
- app/routers/x.py:123  db-access  db.query()  → services/<pkg>/<module>.py::<fn>

Review findings
- app/routers/x.py:140-171  computes margin per dish  → services/<pkg>/<module>.py (reuse <existing fn>)

Clean: <router files reviewed with nothing to move>
```

One line per finding: file:line, what it does, where it moves.

## 7. Install into a repo (on request)

1. Copy `scripts/check_thin_routers.py` into the backend's `scripts/`; set `--routers` /
   `--baseline` / `--database-module` / `--session-dep` defaults to the project's names.
2. Bootstrap the baseline once: `python scripts/check_thin_routers.py --write` (records today's
   debt; from then on it only shrinks). Commit both files.
3. CI: run the check in the backend job. Also fail a PR that RAISES a count vs the base branch
   (compare `git show origin/<base>:<baseline>` with the checkout), or the baseline is self-serve.
4. Write the rule into the repo's agent docs (`CLAUDE.md` / conventions) and copy this skill into
   the repo's `.claude/skills/` with the project's domain map filled in.
