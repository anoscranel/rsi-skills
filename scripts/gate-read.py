#!/usr/bin/env python3
"""gate-read.py — RSI Stage-1 DIAGNOSTIC join-report (leaf-events x harness-outcomes).

DIAGNOSTIC-ONLY — this script DOES NOT evaluate the SPEC section-0 gate.
It reads two JSONL files and reports join integrity and denominators:

  - per-skill leaf event counts
  - join rate WITH denominator (matched leaf events / total leaf events)
  - unmatched counts on each side
  - duplicate (sessionID, callID) keys counted on BOTH sides
  - chain-continuity classified over the canonical history
    (live file first, then the rotated/older file when --outcome2 is given):
    mid-file breaks (inside one file), the rotation boundary
    (live's first `prev` vs the rotated file's last line — reported once,
    labeled), and per-file break counts. When the boundary hash matches,
    the cross-file-intact case prints explicitly.
  - validator_verdict tally on outcome records
  - `--since` / `--until` ISO-8601 window flags on `ts`
    (filter both sides; excluded records are reported)
  - trust-label tally on outcome records
  - malformed-line count in each file

Missing files are reported as `0 events`, not an error. Nothing is written
anywhere; this script only reads and prints. Exit 0 whenever a report is
produced.

Paths default to the opencode locations and can be overridden with
--leaf / --outcome; --outcome2 names a rotated/older outcome file. Multiple
passes for `.2`+ are NOT in scope — one rotation level.
Usage: python3 scripts/gate-read.py --help
"""

import argparse
import datetime
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


def read_lines(path):
    """Return the list of non-blank raw lines (no trailing newline)."""
    lines = []
    if not os.path.isfile(path):
        return lines
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.strip():
                lines.append(line)
    return lines


def join_key(record):
    if not isinstance(record, dict):
        return None
    session = record.get("sessionID")
    call = record.get("callID")
    if session is None or call is None:
        return None
    return (session, call)


def parse_iso_or_none(value):
    """Parse an ISO-8601 timestamp or datetime; return None on failure.

    Python 3.8-safe: fromisoformat() handles 'YYYY-MM-DDTHH:MM:SS' and
    supports a trailing 'Z' only when normalized first.
    """
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def chain_breaks_per_file(path):
    """Count `prev`-field breaks inside ONE file. A break = record i (i>=1)
    whose `prev` differs from the SHA-256 of line i-1 (the raw line as
    written, without its trailing newline). Missing/unreadable file or an
    empty file -> (0, 0)."""
    lines = read_lines(path)
    breaks = 0
    checked = 0
    for index in range(1, len(lines)):
        try:
            record = json.loads(lines[index])
        except ValueError:
            continue
        if isinstance(record, dict) and "prev" in record:
            checked += 1
            if record.get("prev") != sha256_text(lines[index - 1]):
                breaks += 1
    return breaks, checked


def boundary_check(live_path, rotated_path):
    """Classify the rotation boundary: live file's FIRST `prev`-bearing
    record vs the SHA-256 of the ROTATED file's LAST line.

    Returns (status, live_first_prev, rotated_last_hash) where status is
    'match' | 'break' | 'absent-rotated' | 'absent-live' | 'no-prev'.
    All hashes use the raw line as written, without its trailing newline."""
    if not os.path.isfile(rotated_path):
        return "absent-rotated", None, None
    rotated_lines = read_lines(rotated_path)
    if not rotated_lines:
        return "absent-rotated", None, None
    rotated_last_hash = sha256_text(rotated_lines[-1])
    if not os.path.isfile(live_path):
        return "absent-live", None, rotated_last_hash
    live_lines = read_lines(live_path)
    live_first_prev = None
    found = False
    for line in live_lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and "prev" in record:
            live_first_prev = record.get("prev")
            found = True
            break
    if not found:
        return "no-prev", None, rotated_last_hash
    if live_first_prev == rotated_last_hash:
        return "match", live_first_prev, rotated_last_hash
    return "break", live_first_prev, rotated_last_hash


def count_first_prev_checks(path):
    """(present, missing) `prev`-field counts in one file, for the report."""
    present = 0
    missing = 0
    for record, _line in read_records_with_lines(path):
        if isinstance(record, dict):
            if "prev" in record:
                present += 1
            else:
                missing += 1
    return present, missing


def read_records_with_lines(path):
    """[(parsed record or None, raw line)] for a JSONL file; [] if missing."""
    pairs = []
    for line in read_lines(path):
        try:
            pairs.append((json.loads(line), line))
        except ValueError:
            pairs.append((None, line))
    return pairs


def duplicate_tally(records, extra_records):
    """Count of (sessionID, callID) keys appearing more than once, and the
    total number of joinable records, over records + extra_records."""
    counter = Counter()
    for record in records + extra_records:
        key = join_key(record)
        if key is not None:
            counter[key] += 1
    duplicated_keys = sum(1 for count in counter.values() if count > 1)
    total_keyed = sum(counter.values())
    return duplicated_keys, total_keyed


def parse_window(value):
    if value is None:
        return None
    parsed = parse_iso_or_none(value)
    if parsed is None:
        raise argparse.ArgumentTypeError(
            "not an ISO-8601 timestamp: %r" % (value,)
        )
    return parsed


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
    parser.add_argument(
        "--outcome2",
        default=None,
        help=(
            "path to a rotated/older harness-outcomes.jsonl (e.g. "
            "harness-outcomes.jsonl.1). The canonical history is the live "
            "file first, then this file. Multiple passes for `.2`+ are NOT "
            "in scope — one rotation level. Default: no rotated file."
        ),
    )
    parser.add_argument(
        "--since",
        type=parse_window,
        default=None,
        help="ISO-8601 timestamp: only report records with ts >= this (both sides)",
    )
    parser.add_argument(
        "--until",
        type=parse_window,
        default=None,
        help="ISO-8601 timestamp: only report records with ts <= this (both sides)",
    )
    args = parser.parse_args(argv)

    # -- read raw lines once; report file sizes (counts) before anything else.
    leaf_records, leaf_malformed = read_jsonl(args.leaf)
    outcome_records, outcome_malformed = read_jsonl(args.outcome)
    rotated_records = []
    rotated_malformed = 0
    if args.outcome2:
        rotated_records, rotated_malformed = read_jsonl(args.outcome2)

    # -- window filter on ts (both sides; report how many were excluded)
    leaf_windowed = []
    leaf_excluded = 0
    for record in leaf_records:
        if record_in_window(record, args.since, args.until):
            leaf_windowed.append(record)
        else:
            leaf_excluded += 1
    outcome_windowed = []
    outcome_excluded = 0
    for record in outcome_records:
        if record_in_window(record, args.since, args.until):
            outcome_windowed.append(record)
        else:
            outcome_excluded += 1
    rotated_windowed = []
    rotated_excluded = 0
    for record in rotated_records:
        if record_in_window(record, args.since, args.until):
            rotated_windowed.append(record)
        else:
            rotated_excluded += 1

    per_skill = Counter()
    for record in leaf_windowed:
        skill = record.get("skill") if isinstance(record, dict) else None
        per_skill[skill if isinstance(skill, str) else "<missing>"] += 1

    all_outcome_windowed = outcome_windowed + rotated_windowed
    outcome_keys = set()
    trust_tally = Counter()
    validator_present = 0
    validator_tally = Counter()
    for record in all_outcome_windowed:
        if not isinstance(record, dict):
            continue
        key = join_key(record)
        if key is not None:
            outcome_keys.add(key)
        trust = record.get("trust")
        trust_tally[trust if isinstance(trust, str) else "<missing>"] += 1
        if "validator_verdict" in record:
            validator_present += 1
            verdict = record["validator_verdict"]
            validator_tally[
                verdict if isinstance(verdict, str) else repr(verdict)
            ] += 1

    leaf_keys = set()
    matched = 0
    leaf_joinable = 0
    for record in leaf_windowed:
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
    if args.outcome2:
        print("outcome file 2 (rotated/older): %s" % args.outcome2)
    if args.since or args.until:
        print(
            "window: since=%s until=%s"
            % (args.since.isoformat() if args.since else "-",
               args.until.isoformat() if args.until else "-")
        )
        print(
            "window excluded: %d leaf, %d live-outcome, %d rotated-outcome record(s)"
            % (leaf_excluded, outcome_excluded, rotated_excluded)
        )
    print("")
    print("Leaf events (total): %d" % len(leaf_windowed))
    if per_skill:
        for skill in sorted(per_skill):
            print("  %s: %d" % (skill, per_skill[skill]))
    else:
        print("  0 events (no leaf records found)")
    print("Malformed leaf lines: %d" % leaf_malformed)
    print("")
    print("Outcome records (total): %d" % len(outcome_windowed))
    print("Malformed outcome lines: %d" % outcome_malformed)
    if args.outcome2:
        print("Rotated outcome records (total): %d" % len(rotated_windowed))
        print("Malformed rotated outcome lines: %d" % rotated_malformed)
    if trust_tally:
        for trust in sorted(trust_tally):
            print("  trust=%s: %d" % (trust, trust_tally[trust]))
    print("")
    print(
        "duplicate keys: %d of %d outcome keys"
        % duplicate_tally(outcome_windowed, rotated_windowed)
    )
    print(
        "duplicate keys: %d of %d leaf keys"
        % duplicate_tally(leaf_windowed, [])
    )
    print(
        "validator_verdict: %d present"
        % validator_present
    )
    if validator_present:
        for verdict in sorted(validator_tally):
            print("  validator_verdict=%s: %d" % (verdict, validator_tally[verdict]))
    else:
        print("  0 present (recorder does not write this field)")
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
    # -- chain report: per-file mid-file breaks, then the boundary, labeled.
    live_breaks, live_checked = chain_breaks_per_file(args.outcome)
    if live_checked:
        print(
            "Live-outcome chain (`prev`, mid-file): %d break(s) over %d checked link(s)"
            % (live_breaks, live_checked)
        )
    else:
        print("Live-outcome chain (`prev`, mid-file): no `prev`-bearing records checked")
    if args.outcome2:
        rotated_breaks, rotated_checked = chain_breaks_per_file(args.outcome2)
        if rotated_checked:
            print(
                "Rotated-outcome chain (`prev`, mid-file): %d break(s) over %d checked link(s)"
                % (rotated_breaks, rotated_checked)
            )
        else:
            print("Rotated-outcome chain (`prev`, mid-file): no `prev`-bearing records checked")
        status, live_first_prev, rotated_last_hash = boundary_check(
            args.outcome, args.outcome2
        )
        if status == "match":
            print(
                "Rotation boundary: cross-file chain INTACT (live first `prev` "
                "matches the hash of the rotated file's last line)"
            )
        elif status == "break":
            print(
                "Rotation boundary: boundary break (live file's first `prev` "
                "%s does not match the hash of the rotated file's last line %s "
                "— reported as a boundary break, not an error)"
                % (
                    str(live_first_prev)[:12] + "..." if live_first_prev is not None else "<none>",
                    str(rotated_last_hash)[:12] + "..." if rotated_last_hash is not None else "<none>",
                )
            )
        elif status == "absent-rotated":
            print("Rotation boundary: rotated file missing or empty — no boundary checked")
        elif status == "absent-live":
            print("Rotation boundary: live file missing — no boundary checked")
        else:  # no-prev
            print("Rotation boundary: no `prev`-bearing record in the live file — no boundary checked")
    print("")
    print(DIAGNOSTIC_NOTE)
    print("STATUS: GATE NOT EVALUABLE (diagnostic report only)")
    return 0


def record_in_window(record, since, until):
    """True when a record's `ts` falls inside [since, until] (either side
    may be None). Records without a parseable `ts` are kept (reported in
    the totals, never silently dropped)."""
    if record is None or not isinstance(record, dict):
        return True
    if since is None and until is None:
        return True
    stamp = parse_iso_or_none(record.get("ts"))
    if stamp is None:
        return True
    if since is not None and stamp < since:
        return False
    if until is not None and stamp > until:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
