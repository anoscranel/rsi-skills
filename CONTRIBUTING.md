# Contributing

This repo is a specification plus a diagnostic reader. Improvements are proposals, never live edits: **no runtime self-modifying proposals ever**.

**How to propose:** open or comment on a GitHub issue — **propose via GitHub issue**, sketch the change, and name the files and lines it touches. Do not open a pull request before the scope is agreed. Fixtures and reproduction commands for any reader change are welcome in the issue.

**How changes land:** **every change lands through human review**. The owner triages issues, accepts or rejects scope, and applies accepted work in a dated release. The Stage-2 optimizer — typed edit proposals from the logs — is not built and does not merge anything; nothing in this repo writes to a skill tree or to the logs at run time.

**What can change:** **accepted scope = spec/schema/reader text only** — `docs/SPEC-rsi-skills.md`, `skills/ac-rsi/schema/log-schema.md`, `scripts/gate-read.py`, and the README/SECURITY/CHANGELOG text around them. Runtime recorders, harness code, and the Stage-2 optimizer are out of scope (see the SPEC's non-goals, §9).

Safety rules bind contributors too (SPEC §4): logs are append-only, a skill never records its own outcome, and an inconclusive signal produces no proposal.
