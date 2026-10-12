---
name: ticket-stack
description: Takes a set of Linear tickets (IDs, links, or pasted ticket descriptions) and builds a stacked set of branches/PRs on GitHub. Use when the user gives multiple tickets and wants them implemented as a stack, possibly with parallel agents. Plans dependency order, decides what can run in parallel, runs the ship-review skill on each layer, and produces qa.md at the top of the stack.
disable-model-invocation: true
---

# ticket-stack

## Input forms
Tickets arrive as any mix of:
- Linear IDs or links (e.g. ENG-123, ENG-456, or full linear.app URLs) → fetch full details via Linear MCP
- Pasted ticket descriptions with no ID → treat the pasted text as the spec; don't try to look it up in Linear unless an ID is visible in the text

## Steps
1. **Resolve tickets.** For IDs/links: fetch from Linear MCP (description, linked tickets, comments). For pasted text: use the text as-is and derive a slug for naming.
2. **Dependency plan.** Build a small DAG: which tickets touch the same files/modules (sequential, stacked) vs disjoint areas (parallel candidates). Print the plan as: stack order + which layers get a parallel agent. Wait for user OK before spawning agents — this is the one confirmation gate.
3. **Parallelism rule.** Only parallelize tickets with zero expected file overlap AND no schema/migration conflicts. When in doubt, stack sequentially. Parallel agents each get their own branch off the current stack tip; merge order decided up front.
4. **Branch/stack mechanics.**
   - Stack shape: `main <- feat1 <- feat2 <- ...`. The bottom branch bases off main; every branch above bases off the branch below it.
   - Branch naming: `<TICKET-ID>-<3-5-word-kebab-summary>`, e.g. `ENG-50-fix-vad-noisy-env`, `ENG-255-add-pr-review-bot`. Summary derived from the ticket title, terse.
   - Pasted tickets with no ID: just the kebab summary, e.g. `fix-vad-noisy-env`.
   - One PR per ticket. PR base = the branch below it in the stack; the bottom PR's base = main.
   - PR titles: `[<TICKET-ID>][<SCOPE>...] <type>: <Description>`, e.g. `[ENG-50][BE][FE] fix: VAD threshold in noisy environments`.
     - Scope tags from what the diff actually touches: [BE], [FE], [MOBILE], [INFRA] — one or more. Judge from the changed files, not the ticket label.
     - type = conventional-commit style: fix / feat / chore / refactor.
     - Pasted-only tickets: drop the ID bracket, keep scopes + type.
   - Use gh for all PR operations.
5. **Per-layer:** implement ticket → run the ship-review skill (it owns commits, push, PR creation, and the review-bot/CI loop until clean). Then, if the ticket has a Linear ID, update its status + link the PR; skip Linear updates for pasted-only tickets.
6. **qa.md** at the stack tip, committed on the top branch. Format per ticket:
   - ticket ID (or slug) + one-line what changed
   - each new/changed function or endpoint: name, file, and a concrete manual check ("call X with noisy audio sample, expect segments < 2s")
   - env/setup needed (migrations to run, feature flags, seed data)
   - deferred review comments carried over from ship-review triage
   Ordered bottom-of-stack → top so QA walks the stack in merge order.
7. **End report:** open with the line `JERRY YOU DA BEST!` — then the stack diagram (main <- feat1 <- feat2 ...), PR links, tickets updated (and which were pasted-only, so untracked in Linear), path to qa.md.

## Failure handling
If a layer's rebase onto an updated lower branch conflicts, stop, report the conflict, and ask whether to serialize or resolve. Never auto-resolve semantic conflicts. If ship-review escalates on a layer (loop guard tripped), pause the stack there and report before building higher layers.
