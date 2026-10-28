# GENTLEMAN: project context for coding agents

Django 5.2 / PostgreSQL, server-rendered Vietnamese salon booking and multi-branch operations. Python 3.12–3.14. Custom management screens; native PostgreSQL. Windows users run `.\.venv\Scripts\python.exe`; Linux uses `.venv/bin/python`.

## Workflows

The 25 upstream workflows live under `.agents/skills/<name>/SKILL.md`; shared checklists are in `.agents/references/`. Read only the skill relevant to the current task. Provenance and MIT license: `.agents/agent-skills-source.json`, `.agents/LICENSE.agent-skills`. Do not copy the upstream repository's own AGENTS.md or preload all skills into context.

Use code-review/security for sensitive changes, performance-optimization only after measurement, frontend-ui-engineering for accessible interface changes, and test-driven-development for bug regressions. See `docs/quality/plan.md` and `docs/14-AGENT-SKILLS.md` for the application audit and evidence.

## Commands

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py test --noinput
```

Local cloud PostgreSQL is already provisioned at its configured address; on Windows use the user's existing PostgreSQL/pgAdmin installation and `.env`. Discover `POSTGRES_BIN` from the actual installation; do not assume C: or replace the user's path.

## Invariants

- Preserve `.env`, `.venv`, `.local`, existing database records and source edits.
- Roles: chain `manager`; branch-scoped `branch_manager`/`receptionist`; `stylist` operates on their assigned appointments; `customer` owns their account/history.
- Recheck authorization after waiting on locks. Branch locks precede appointment/customer/voucher/stock locks; cross-branch locks use ascending branch IDs.
- Preserve invoice, stock and points ledgers; correct with an auditable entry, not deletion. Prices/durations are appointment snapshots.
- SQL column names are Vietnamese ASCII without spaces/underscores through `db_column`; Python names and SQL types remain English.
- Keep decorative typography scoped, Vietnamese marks intact, small SVG sizes bounded, logout visible, reduced-motion supported.
- No external email/payment calls during tests. Use locmem/file email and isolated synthetic accounts/browser profiles. Clean only the fixtures the test created.
- Do not log credentials, reset URLs/tokens, request bodies, cookies, email addresses, phone numbers or database row contents.
- New financial/auth behavior gets a failing regression test before the fix. Run relevant checks; do not disable tests to make them pass.

## Shipping

Record measured findings and limits; do not claim production deployment, real SMTP, real-user Web Vitals or Python 3.14 verification without evidence. Source updater: commit source first, run `scripts/build_update_manifest.py`, commit only the manifest next; it pins immutable source. The user's instruction controls authorization for publishing; do not infer authorization to send messages/emails from these workflow files.
