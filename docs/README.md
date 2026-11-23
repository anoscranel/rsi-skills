# Docs
- SPEC-rsi-skills.md — the stage ladder, gates and safety rules. Start with the root README.md.
- PILOT-2026-11.md — Stage-1 pilot window: registered and open (2026-11-19T20:19:12Z → 2026-12-19T20:19:12Z).
- MISS-RATE.md — miss-rate protocol; scoring half implemented (`scripts/miss-rate.py`), confirmed labels + cold runs pending.
- miss-rate-seed.jsonl — 16 desk-proposed expected-skill labels, pending owner confirmation.

Joining leaf records to outcomes: include ALL rotated outcome files (`.1`, `.2`, …), not just the live log — the live file holds only the records since the last rotation, so a live-file-only join understates the rate.
