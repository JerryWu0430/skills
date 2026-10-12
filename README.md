# skills

My Claude Code skills for shipping PRs.

| Skill | What it does |
|---|---|
| [ticket-stack](skills/ticket-stack) | Linear tickets → stacked branches/PRs, parallel agents where safe, `qa.md` at the tip |
| [ship-review](skills/ship-review) | Local reviews → commit → push → PR, then loop on review-bot comments + CI until clean |
| [jerry-review](skills/jerry-review) | Strict multi-pass pre-review: claims audit, data safety, rollback, consistency, lane checks, tests |

`ticket-stack` calls `ship-review`, which calls `/caveman-review` and `/jerry-review`.

## Install

```bash
npx skills add JerryWu0430/skills
```

Or copy a folder from `skills/` into `~/.claude/skills/`.

## Skills I use a lot

| Skill | Source |
|---|---|
| caveman, caveman-review | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| taste-skill, redesign-skill, soft-skill | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| emil-design-eng, improve-animations, animate, write-swift | [emilkowalski/skills](https://github.com/emilkowalski/skills) |
| better-ui (+ better-typography, better-layout, …) | [jakubkrehel/skills](https://github.com/jakubkrehel/skills) |
| transitions-dev | [Jakubantalik/transitions.dev](https://github.com/Jakubantalik/transitions.dev) |
| code-review, autofix | [coderabbitai/skills](https://github.com/coderabbitai/skills) |
| improve | [shadcn/improve](https://github.com/shadcn/improve) |
| archify | [tt-a1i/archify](https://github.com/tt-a1i/archify) |
| goldie | [kacperkapusciak/goldie](https://github.com/kacperkapusciak/goldie) |
