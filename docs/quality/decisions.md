# Decisions from the Agent Skills review

## ADR 014: portable, pinned workflows (accepted)

Context: the owner uses VS Code and copies updates by file. The upstream collection is workflow documentation, not an application runtime dependency. Decision: vendor the 25 skills and references under `.agents/`, retain MIT/provenance/SHA256, and route through a small project AGENTS.md and Copilot instructions. Read relevant files on demand. Consequence: offline review is possible; upstream updates are deliberate source changes and can be verified with `scripts/verify_agent_skills.py`. No upstream bootstrap script or global installation runs.

## ADR 015: shared authentication counters in PostgreSQL (accepted)

Context: native PostgreSQL already serves all workers; in-memory reset counters do not coordinate them. Decision: short-lived HMAC keys, atomic row-locked counters and bounded expired-key cleanup, with a maintenance command. Normalize login identifiers using the login form's strip rule, ignore arbitrary forwarding headers. Consequence: no extra database service/Docker; each credential POST has database work, and a trusted proxy must set the actual client address. Limits are temporary per-client, not permanent account locks.

## ADR 016: append-only points recovery (accepted)

Context: restoring redeemed points after an earlier refund could leave both spendable points and recovery debt, making future awards depend on refund order. Decision: offset returned points against debt in the same customer lock; record gross debt added and debt repaid on the refund. Normalize legacy overlapping balances with an appended `debt_recovery` entry. Consequence: preserve net entitlement and old invoices/entries; schema rollback does not reverse financial corrections. Backup and the migration regression cover the upgrade.

## ADR 017: grouped reads before caching (accepted)

Context: measured query counts grew with branch/stylist/history count. Decision: independent grouped aggregates, joined related objects, batched schedule reads and bounded history pagination. Consequence: lower query counts without stale cached permissions, capacity or money. Query budgets constrain regressions; they are small-data measurements, not production throughput promises.
