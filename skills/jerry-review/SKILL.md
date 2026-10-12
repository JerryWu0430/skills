---
name: jerry-review
description: >
  Strict pre-review of a PR so a senior reviewer's pass finds nothing. Audits PR-body
  claims against the diff, hunts cross-account/org data leakage, missing rollback stories,
  auth gates skipped at one layer, duplicate logic, mobile ANR/store-policy/UI-perf
  risks, backend migration/storage discipline, cross-client contract drift, and untested
  risky paths. Use when user says "jerry review", "pre-review", "review before merge",
  or invokes /jerry-review.
---

Review the current branch/PR the way a strict senior reviewer would, then fix what they'd flag. Assume they run multi-pass AI reviews (domain reviewers + cross-cutting passes) plus review bots — anything below WILL be found.

## Step 0 — Gather

- PR exists: `gh pr view --json title,body,files` + `gh pr diff`. No PR yet: diff branch vs `main`.
- Identify repo lane: android / backend / ios / frontend / infra. Pick lane checks below.
- Kick off any available review bot in parallel (e.g. `/code-review`) — clear its findings pre-emptively.
- Large PR (>~30 files): fan out parallel subagents, one per domain pass below, then merge findings.

## Pass 1 — Claims audit (do this first, never skip)

Extract EVERY factual claim from: PR title/body, checklists/docs touched in the diff, code comments describing behavior or contracts. Verify each against the actual diff + code. Most common findings:

- Body says a fallback/kill-switch exists → env var appears nowhere in branch, fallback modules actually deleted. The advertised safety story doesn't exist.
- Wrong counts/status: "173 tests" when suite is 199; checklist says a feature is kept while branch deletes it.
- Stale description after re-scoping: reviewers end up reviewing fiction.
- Code comments describing an API contract the backend doesn't have.

Fix: make body/docs/comments match the final diff. Rewrite the PR description LAST, after all fixes land.

## Pass 2 — Data safety & auth (blocker class)

- **Cross-account/org leakage**: every fetched list scoped to the signed-in user? (e.g. org-scoped endpoint restores other users' records to device). Filter client-side by owner when backend returns broader scope.
- **Wipe races**: account-switch wipe vs in-flight writes — generation checks must be validated UNDER the same lock as the store write, not before it.
- **Consent flows**: server withdrawal reconciled on other devices; withdraw vs in-flight grant POST serialized.
- **Auth gates at every layer**: a permission enforced at session-create but not in a downstream layer = mid-session bypass. Make it consistent, filter there too, and test that the restricted path is actually blocked.
- **Irreplaceable data fails hard**: writes of customer input (templates, signed documents) must not swallow storage errors and log-only. Regenerable derivatives may.
- No PII/tokens/transcripts in logs.

## Pass 3 — Rollback & failure story

- Cold start with the dependency down: does the app/service still work? What's the actual rollback lever?
- Unknown input → safe default (log-and-skip), never "route to the wrong bucket/branch".
- Permanent-failure loops: a 4xx that isn't retryable must not drop data (401 mid-token-refresh ≠ 404); a permanently-failing fetch must not retry forever.

## Pass 4 — Consistency / single source of truth

- One parser/helper per job — flag the 2nd and 3rd duplicate and name which shared one to use.
- One key/naming convention (e.g. `{type}/{org}/{id}` — no exceptions).
- One enforcement point, one UI per concept — fold split editing surfaces together.
- New code must use the repo's existing correct pattern; cite the in-repo file that does it right.

## Pass 5 — Lane checks

**Android** (treat these as blockers):
- ANR: no main-thread crypto/file IO/`Thread.sleep`/PackageManager sweeps — sign-out wipes and click handlers especially. Move to IO coroutine (`NonCancellable` where needed).
- Play policy: user-visible strings make no misleading claims; every FGS in manifest covered in Play Console declaration + demo video; data-safety copy matches actual backend vendors.
- Compose perf: no per-frame recomposition (frame-clock/drag reads only inside draw/`graphicsLayer`); don't collapse LazyColumn `items` into one eager `item`; O(rows×contacts) scans capped.
- State: `rememberSaveable` (not `remember`) for anything user-entered; tab switches need `SaveableStateHolder`; check activity-recreation + process-death paths.
- i18n: no hardcoded user-visible strings; key + placeholder parity across all locales.
- Build: AGP version syncs in current Studio; JDK toolchain matches docs + CI.

**Backend**:
- Schema/data changes are migrations, never boot-time seed scripts; migrations append-only.
- Object storage: buckets separated by replaceability class (irreplaceable input / regenerable derivative / user media), org segment in every key, versioning on compliance-record buckets.
- Every endpoint org/owner-scoped; super-admin bypasses intentional.
- Deploy deps (infra PRs, env vars) listed in PR body with ordering.

**Cross-client contract** (any lane):
- Verify paths/enums/fields against the live counterpart repo code, not the docs.
- Server-driven content dropped by hardcoded client catalogs = defeats the feature's purpose. If out of scope: create the ticket now so it doesn't get lost.

## Pass 6 — Tests

- Every risky path found above needs a test; list them by name (wipe ordering, auth error classification, restricted-org filtering, transient-vs-definitive retry split).
- Vacuous tests flagged: would it still pass if the feature were deleted? Assert the actual behavior.
- Interface-faked tests don't cover the real impl — if `FooImpl` never executes in any test, say so.

## Output format

```
## 🔴 Blockers      — merge-stoppers; file:line, concrete failure scenario, minimal fix
## 🟡 Risks         — grouped by domain; same anatomy
## 🔵 Nits / ❓     — small fixes + open questions
## Verified clean   — what was checked and found fine (proves coverage)
```

Every finding = `file:line` + concrete failure scenario with real numbers ("notes drift up to ~17 min", "5-hour error") + minimal concrete fix + test ask. No speculation — verify each finding in code before reporting; unverifiable ones go to ❓.

## Then

1. Fix blockers, then risks; nits if cheap.
2. Re-run the claims audit against the final diff; rewrite PR description to match.
3. Confirm review-bot findings addressed.
