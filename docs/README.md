# Docs
- SPEC-rsi-skills.md — the stage ladder, gates and safety rules. Start with the root README.md.
- PILOT-2026-11.md — Stage-1 pilot-window template (not pre-registered).
- MISS-RATE.md — miss-rate protocol (not implemented).

Joining leaf records to outcomes: include ALL rotated outcome files (`.1`, `.2`, …), not just the live log — the live file holds only the records since the last rotation, so a live-file-only join understates the rate.
