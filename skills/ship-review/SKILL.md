---
name: ship-review
description: End-of-work review-and-ship loop. Use when finishing a feature, a QA list item, or any chunk of work — or when the user says "ship it", "wrap this up", "review and commit", or "run reviews". Runs local reviewers (/caveman-review, /jerry-review, plus guard skills like /thin-routers when their area changed), commits, pushes, creates/updates the PR with gh, then monitors review-bot comments (CodeRabbit, Greptile, Devin, Bugbot — whatever the repo has) and CI, looping fixes until no comments remain and CI is green. Can be invoked multiple times on the same branch.
---

# ship-review

## Phase 1 — local (pre-push)
1. **Scope the diff.** `git diff <base>...HEAD` plus unstaged. Base = merge-base with the branch this stacks on (main if this is the bottom of the stack).
2. **Local reviews.** Run /caveman-review and /jerry-review on the diff. Also run every guard skill whose area the diff touches: `/thin-routers` when backend router files changed, plus any guard the repo ships in `.claude/skills/`. A guard's failing check is fix-now. Collect comments, dedupe.
3. **Triage.** fix-now / ticket-later / dismiss-with-reason. Fix the fix-nows. List deferred/dismissed to the user — never silently drop.
4. **Local checks.** Run lint + typecheck + tests (check package.json / Makefile / CI config for the canonical commands). Fix failures before committing.
5. **Commit.** One commit per coherent behavior change. Test: each commit revertable alone, app still builds. 2-6 commits for multi-part work is right; squash 10+ tiny ones, split one giant one.
   - Message style: terse, imperative, grammar sacrificed for density. `fix vad threshold noisy env, drop dead config path`. No body unless migration/breaking change.

## Phase 2 — push + PR
6. **Push.** `git push -u origin <branch>` (plain push on re-runs).
7. **PR via gh.** If none exists: `gh pr create` with body from /pr-description, base = the branch below in the stack, or main for the bottom branch. If exists: `gh pr edit` to append a terse "since last push:" section — don't rewrite the whole body.
   - Media: follow /pr-description's Media step right after the PR exists. Attach the screenshots and video the verify run captured (upload via Chrome, then `gh pr edit`). On re-runs, add new media under "since last push:" instead of replacing old.
   - Title format: `[<TICKET-ID>][<SCOPE>...] <type>: <Description>` — infer ticket ID from the branch name, scopes ([BE]/[FE]/[MOBILE]/[INFRA]) from the changed files, type = fix/feat/chore/refactor.
8. **Detect review bots.** Whatever the repo has installed — CodeRabbit, Greptile, Devin, Bugbot, etc. Check past PRs (`gh pr view <recent> --comments`) to see which post. Never skip one that's installed.

## Phase 3 — remote loop (repeat until clean)
9. **Wait for bots + CI.** Poll with `gh pr checks <num>` and `gh api repos/{owner}/{repo}/pulls/{num}/comments` + `gh pr view --comments`. Give the bots a few minutes to post; poll with backoff (60s, then 120s), don't hammer.
10. **Collect remote comments.** All review-bot comments since last push. Dedupe across bots and against already-addressed local comments.
11. **Triage same as step 3.** Fix fix-nows, run local checks (step 4), commit (terse style), push.
    - For dismissed bot comments: reply on the PR thread with a one-line reason (`gh pr comment` or `gh api` reply) so the thread isn't left dangling.
12. **CI.** If any check fails, read the failure log (`gh run view --log-failed`), fix, commit, push. CI green is a hard exit requirement.
13. **Loop** back to step 9 after every push. Exit only when: zero unresolved bot comments (excluding explicitly-dismissed-with-reply ones) AND all CI checks green AND lint/tests pass.
14. **Loop guard.** If after 3 full cycles the same comment class keeps recurring or CI keeps failing on the same check, stop and escalate to the user with a summary instead of thrashing.

## End state report
Open with the line: `JERRY YOU DA BEST!` — then:
- commits made this invocation
- PR link, CI status (green)
- comments addressed vs dismissed-with-reason vs deferred-to-ticket
- anything escalated

## Repeat invocation
Safe to run per QA-list item on the same branch. On re-runs, only diff/review since the last ship-review boundary; the remote loop still checks ALL open unresolved bot comments on the PR, not just new ones.
