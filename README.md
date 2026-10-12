# skills

My Claude Code skills for shipping PRs.

| Skill | What it does |
|---|---|
| [ticket-stack](skills/ticket-stack) | Linear tickets → stacked branches/PRs, parallel agents where safe, `qa.md` at the tip |
| [ship-review](skills/ship-review) | Local reviews → commit → push → PR, then loop on Greptile/CodeRabbit/CI until clean |
| [jerry-review](skills/jerry-review) | Strict multi-pass pre-review: claims audit, data safety, rollback, consistency, lane checks, tests |

`ship-review` calls `/caveman-review` ([caveman](https://github.com/JuliusBrussee/caveman)) and `/jerry-review`. `ticket-stack` calls `ship-review`.

## Install

```bash
npx skills add JerryWu0430/skills
```

Or copy a folder from `skills/` into `~/.claude/skills/`.
