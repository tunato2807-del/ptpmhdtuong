# GENTLEMAN

Follow `AGENTS.md` for this Django/PostgreSQL project. Engineering workflows from addyosmani/agent-skills are pinned in `.agents/skills/`; read the relevant SKILL.md when reviewing security, fixing a bug, changing UI, profiling performance, or updating CI. Shared references are in `.agents/references/`. Use progressive disclosure rather than loading all 25 skills.

Keep multi-branch permission checks, financial history and Vietnamese column naming intact. Work on a complete small change with a regression test and verification evidence. Keep fonts scoped to selected UI components. Use the existing native PostgreSQL setup and preserve local configuration/database. Never put credentials, reset tokens or customer contact data in source, logs or review prompts.

Spec Kit v1.3.0 is configured with Copilot skills in `.github/skills/speckit-*/` (chat syntax `/speckit-specify`, `/speckit-plan`, etc.). Read `.specify/memory/constitution.md` and only the active `specs/<id>/` artifacts. Generated Python examples should use the project's `.venv` interpreter, especially on Windows. `.specify/feature.json` is local state. Keep CLI dependencies out of the Django runtime; native lifecycle events remain disabled. The user's established authorization controls the scope; do not ask again merely because a template shows a review step. See `docs/16-SPEC-KIT.md`.
