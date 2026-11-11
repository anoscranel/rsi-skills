#!/usr/bin/env python3
"""gate-read.py — RSI Stage-1 DIAGNOSTIC join-report (leaf-events x harness-outcomes).

DIAGNOSTIC-ONLY — this script DOES NOT evaluate the SPEC section-0 gate.
It reads two JSONL files and reports join integrity and denominators:

  - per-skill leaf event counts
  - join rate WITH denominator (matched leaf events / total leaf events)
  - unmatched counts on each side
  - chain-continuity breaks in the outcome log via the `prev` field
    (a break = any record whose `prev` does not match the SHA-256 of the
    preceding line; the first record's `prev` is not a break)
  - trust-label tally on outcome records
  - malformed-line count in each file

Missing files are reported as `0 events`, not an error. Nothing is written
anywhere; this script only reads and prints. Exit 0 whenever a report is
produced.

Paths default to the opencode locations and can be overridden with
--leaf / --outcome. Usage: python3 scripts/gate-read.py --help
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

DEFAULT_LEAF = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode", "rsi", "leaf-events.jsonl"
)
DEFAULT_OUTCOME = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode", "rsi", "harness-outcomes.jsonl"
)

DIAGNOSTIC_NOTE = (
    "DIAGNOSTIC-ONLY: this report does not evaluate the SPEC section-0 gate."
)


def sha256_text(line):
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def read_jsonl(path):
    """Return (records, malformed_count) for a JSONL file; ([], 0) if missing."""
    records = []
    malformed = 0
    if not os.path.isfile(path):
        return records, malformed
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                malformed += 1
    return records, malformed


def join_key(record):
    if not isinstance(record, dict):
        return None
    session = record.get("sessionID")
    call = record.get("callID")
    if session is None or call is None:
        return None
    return (session, call)


def chain_breaks(path):
    """Count `prev`-field breaks. A break = record i (i>=1) whose `prev`
    differs from the SHA-256 of line i-1 (the raw line as written, without
    its trailing newline). The first record has no predecessor, so its
    `prev` is not checked. Missing/unreadable file -> (0, 0, 0)
    (breaks, checked, skipped_no_prev)."""
    if not os.path.isfile(path):
        return 0, 0, 0
    breaks = 0
    checked = 0
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        prev_line = None
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if prev_line is not None:
                try:
                    record = json.loads(line)
                except ValueError:
                    record = None
                if isinstance(record, dict) and "prev" in record:
                    checked += 1
                    if record.get("prev") != sha256_text(prev_line):
                        breaks += 1
            prev_line = line
    return breaks, checked, 0


def main(argv):
    parser = argparse.ArgumentParser(
        prog="gate-read.py",
        description=(
            "RSI Stage-1 DIAGNOSTIC join-report for leaf-events.jsonl and "
            "harness-outcomes.jsonl. DIAGNOSTIC-ONLY: it does NOT evaluate "
            "the SPEC section-0 gate."
        ),
        epilog=DIAGNOSTIC_NOTE,
    )
    parser.add_argument(
        "--leaf",
        default=DEFAULT_LEAF,
        help="path to leaf-events.jsonl (default: %(default)s)",
    )
    parser.add_argument(
        "--outcome",
        default=DEFAULT_OUTCOME,
        help="path to harness-outcomes.jsonl (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    leaf_records, leaf_malformed = read_jsonl(args.leaf)
    outcome_records, outcome_malformed = read_jsonl(args.outcome)

    per_skill = Counter()
    for record in leaf_records:
        skill = record.get("skill") if isinstance(record, dict) else None
        per_skill[skill if isinstance(skill, str) else "<missing>"] += 1

    outcome_keys = set()
    trust_tally = Counter()
    for record in outcome_records:
        if not isinstance(record, dict):
            continue
        key = join_key(record)
        if key is not None:
            outcome_keys.add(key)
        trust = record.get("trust")
        trust_tally[trust if isinstance(trust, str) else "<missing>"] += 1

    leaf_keys = set()
    matched = 0
    leaf_joinable = 0
    for record in leaf_records:
        if not isinstance(record, dict):
            continue
        key = join_key(record)
        if key is None:
            continue
        leaf_joinable += 1
        leaf_keys.add(key)
        if key in outcome_keys:
            matched += 1
    unmatched_leaf = leaf_joinable - matched
    unmatched_outcome = len(outcome_keys - leaf_keys)

    print("RSI Stage-1 diagnostic join-report")
    print("leaf file:      %s" % args.leaf)
    print("outcome file:   %s" % args.outcome)
    print("")
    print("Leaf events (total): %d" % len(leaf_records))
    if per_skill:
        for skill in sorted(per_skill):
            print("  %s: %d" % (skill, per_skill[skill]))
    else:
        print("  0 events (no leaf records found)")
    print("Malformed leaf lines: %d" % leaf_malformed)
    print("")
    print("Outcome records (total): %d" % len(outcome_records))
    print("Malformed outcome lines: %d" % outcome_malformed)
    if trust_tally:
        for trust in sorted(trust_tally):
            print("  trust=%s: %d" % (trust, trust_tally[trust]))
    print("")
    denominator = leaf_joinable
    if denominator:
        rate = (100.0 * matched) / denominator
        print(
            "Join rate: %d/%d matched (%.2f%%)"
            % (matched, denominator, rate)
        )
    else:
        print("Join rate: 0/0 matched (no joinable leaf events — denominator 0)")
    print("Unmatched leaf events (joinable, no outcome): %d" % unmatched_leaf)
    print("Unmatched outcome keys (no leaf event): %d" % unmatched_outcome)
    print("")
    breaks, checked, _ = chain_breaks(args.outcome)
    if checked:
        print(
            "Outcome chain (`prev`): %d break(s) over %d checked link(s)"
            % (breaks, checked)
        )
    else:
        print("Outcome chain (`prev`): no `prev`-bearing records checked")
    print("")
    print(DIAGNOSTIC_NOTE)
    print("STATUS: GATE NOT EVALUABLE (diagnostic report only)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
