# Agent Skills application plan

- [x] Read/pin the skill catalog and applicable workflows; inspect existing conventions.
- [x] Fresh-context adversarial review of auth/contact and financial transaction boundaries.
- [x] Reproduce and fix contact-email takeover, reset stale writes, post-lock role/assignment rechecks, and order-dependent points refunds.
- [x] Measure and remove query growth on branch overview, resource lists, schedule and appointment history.
- [x] Audit accessibility, loading/error states, security headers and browser data exposure; fix and verify.
- [x] Add shared authentication throttling and safe request observability appropriate for PostgreSQL, plus dependency/static/CI gates.
- [x] Full PostgreSQL verification, browser audit ledger and documentation.
- [ ] Verify immutable update manifest and publish source.

## Review hypotheses (not provided to reviewers)

- Auth/contact paths must never let branch staff take ownership of a customer's login or recover another branch's private history.
- Resetting a password must preserve concurrently updated role, active state, contacts and financial balances.
- Financial ledgers must preserve net points entitlement regardless of refund order, and post-lock checks must reflect current permissions/assignment.

## Independent review reconciliation

Two fresh-context reviewers, same model family, reviewed isolated artifacts/contracts without these hypotheses. Findings: contact-email takeover; Django reset unrestricted stale save; chain-only create checks missing after lock; revoked stylist assignment accepted after lock; refund-order points/debt mismatch. All were reproduced and corrected. On changed artifacts in cycle 2, financial review found no substantive issue; auth review found username-whitespace rate-limit bypass. A failing regression reproduced that bypass; the limiter now uses the form's whitespace normalization. Additional-model review was offered according to the skill; the user explicitly selected the existing reviews. No external model CLI was invoked. Bounded at two review cycles.

## Evidence and decisions

See `docs/validation/14-AGENT-SKILLS.txt`, browser before/after JSON, and `docs/quality/decisions.md`. Initial regression suite: 11 tests, 10 failures (reverse refund order already passed). Final suite: 179 PostgreSQL tests pass. Mutation experiment removed the new post-lock assignment guard; the regression failed, then the exact file was restored. Four query budgets are enforced. Python formatting was checked to have identical ASTs before/after for every reformatted file.

## Verification commands

Runtime: `python scripts/dev.py check` (native PostgreSQL). Focused tests first, then full suite. Browser checks use the existing local DEBUG guard and isolated synthetic accounts. Before/after query and accessibility data will be recorded under `docs/validation/`.
