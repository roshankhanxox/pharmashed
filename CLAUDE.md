# CLAUDE.md

Project: **PharmaShed** — see CONTEXT.md for the brief.

## Every session
1. Read `CONTEXT.md` and `CHECKPOINT.md`. Do not read other docs up front.
2. Work on exactly one module (the one the user names, or the first in CHECKPOINT "Next up").
3. Load only that module's section: `sed -n '/^## Mxx/,/^## Myy/p' IMPLEMENTATION.md` (plus Part A4 equations if the module touches the model).
4. Open only the files that module touches.
5. Finish when the module's acceptance list passes, then update `CHECKPOINT.md` per its protocol and commit with `Mxx: <summary> [checkpoint]`.

## Hard rules (from CONTEXT §5, repeated because they matter most)
- Never invent a scientific number (drug parameters, consumption, PNEC, LOD, excretion, removal). Leave `status=todo` and add a human task to CHECKPOINT instead.
- Never read `data/observed/` outside `engine/src/pharmashed/checks/`.
- Never call the score a probability or say a stream is safe/unsafe.
- Data shapes change only via `contracts/` schemas → regenerate fixtures and types → log a decision in CONTEXT §4.
- Out-of-module changes go into CHECKPOINT "Follow-ups", not into the code.

## Style
- Prefer editing files over rewriting them. Keep explanations short.
- Python: 3.12, uv, ruff, pytest, type hints, pydantic v2.
- Web: Vite + React + TS strict, Zustand, Tailwind, hand-written SVG charts.
- Run the relevant tests before declaring a module done; paste only failures.

## Git workflow
- Remote: `origin` = https://github.com/roshankhanxox/pharmashed.git (`main` is the default branch).
- Never commit directly to `main`. Create a feature branch per module/task (e.g. `Mxx-short-desc`), commit there, and open a PR into `main`.
- Do not add any Claude/AI attribution (no `Co-Authored-By`, no "Generated with Claude Code" lines, no similar footers) to commit messages or PR descriptions.
