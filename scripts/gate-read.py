#!/usr/bin/env python3
"""gate-read.py — RSI Stage-1 DIAGNOSTIC join-report (leaf-events x harness-outcomes).

DIAGNOSTIC-ONLY — this script DOES NOT evaluate the SPEC section-0 gate.
It reads two JSONL files and reports join integrity and denominators:

  - per-skill leaf event counts
  - join rate WITH denominator (matched leaf events / total leaf events)
  - unmatched counts on each side
  - duplicate (sessionID, callID) keys counted on BOTH sides
  - chain-continuity classified over the canonical history
    (live file first, then each rotated/older file given with --outcome2, in
    the order supplied): mid-file breaks (inside each file), EVERY rotation
    boundary in the chain — each newer file's first `prev` against the
    SHA-256 of the older file's last line, reported per boundary and labeled
    (numbered when two or more rotated files are given, the existing
    single-boundary line when exactly one is) — and per-file break counts.
    When a boundary hash matches, the cross-file-intact case prints
    explicitly.
  - validator_verdict tally on outcome records
  - `--since` / `--until` ISO-8601 window flags on `ts`
    (filter both sides; excluded records are reported)
  - trust-label tally on outcome records
  - malformed-line count in each file

Missing files are reported as `0 events`, not an error. Nothing is written
anywhere; this script only reads and prints. Exit 0 whenever a report is
produced.

Paths default to the opencode locations and can be overridden with
--leaf / --outcome; --outcome2 names a rotated/older outcome file and may be
repeated for `.2`, `.3`, … (nearest-newest first) — the boundary check then
chains across every file, newest to oldest.
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


def boundary_check(newer_path, older_path):
    """Classify ONE rotation boundary: the NEWER file's first `prev`-bearing
    record vs the SHA-256 of the OLDER file's LAST line.

    Returns (status, newer_first_prev, older_last_hash) where status is
    'match' | 'break' | 'absent-rotated' | 'absent-live' | 'no-prev'.
    (The 'absent-rotated'/'absent-live' names are kept for call-site
    compatibility: they mean "older file absent/empty" and "newer file
    absent" respectively.) All hashes use the raw line as written, without
    its trailing newline."""
    if not os.path.isfile(older_path):
        return "absent-rotated", None, None
    older_lines = read_lines(older_path)
    if not older_lines:
        return "absent-rotated", None, None
    older_last_hash = sha256_text(older_lines[-1])
    if not os.path.isfile(newer_path):
        return "absent-live", None, older_last_hash
    newer_lines = read_lines(newer_path)
    newer_first_prev = None
    found = False
    for line in newer_lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and "prev" in record:
            newer_first_prev = record.get("prev")
            found = True
            break
    if not found:
        return "no-prev", None, older_last_hash
    if newer_first_prev == older_last_hash:
        return "match", newer_first_prev, older_last_hash
    return "break", newer_first_prev, older_last_hash


def boundary_chain(live_path, rotated_paths):
    """Walk the canonical order [live, rotated[0], rotated[1], …] and return
    one (newer_label, older_label, status, newer_first_prev, older_last_hash)
    tuple per ADJACENT pair, newest first. Labels are 'live' for the live
    file and the basename for a rotated file. Absent/empty files are
    classified, never raised."""
    labels = ["live"] + [os.path.basename(path) for path in rotated_paths]
    paths = [live_path] + list(rotated_paths)
    pairs = []
    for index in range(len(paths) - 1):
        status, prev, last_hash = boundary_check(paths[index], paths[index + 1])
        pairs.append((labels[index], labels[index + 1], status, prev, last_hash))
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


def read_skill_events(paths, adapter):
    """Return (events, malformed) where each event is (sessionID, skill, ts).

    adapter 'opencode': tool_use lines whose part.tool == "skill";
    skill = part.state.input.id, ts = timestamp or ts.
    adapter 'json': flat {"sessionID", "skill", "ts"} per line.
    Unreadable/missing files contribute nothing (report shows 0)."""
    events = []
    malformed = 0
    for path in paths or []:
        if not os.path.isfile(path):
            continue
        for line in read_lines(path):
            try:
                record = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if not isinstance(record, dict):
                malformed += 1
                continue
            if adapter == "opencode":
                part = record.get("part") if record.get("type") == "tool_use" else None
                if not isinstance(part, dict):
                    continue
                if part.get("tool") != "skill":
                    continue
                state = part.get("state") or {}
                skill = (state.get("input") or {}).get("id")
                sid = record.get("sessionID") or part.get("sessionID")
                ts = record.get("timestamp") or record.get("ts")
            else:
                skill = record.get("skill")
                sid = record.get("sessionID")
                ts = record.get("ts")
            if not isinstance(skill, str) or not skill:
                malformed += 1
                continue
            events.append((sid, skill, ts))
    return events, malformed


def report_skill_events(paths, adapter):
    """Print the skill-activation section. Session-level association only:
    activation records carry no callID, so per-skill outcome rates are NOT
    derivable and are deliberately not printed."""
    events, malformed = read_skill_events(paths, adapter)
    print("Skill activations (%d record(s), adapter=%s)" % (len(events), adapter))
    if not events:
        print("  0 skill activations (no records found)")
        if malformed:
            print("  malformed: %d" % malformed)
        return
    tally = Counter(skill for _sid, skill, _ts in events)
    sessions = set(sid for sid, _s, _t in events if sid)
    for skill in sorted(tally):
        print("  %s: %d" % (skill, tally[skill]))
    print("  distinct skills: %d" % len(tally))
    print("  sessions with an activation: %d" % len(sessions))
    print("  attribution: session-level (no callID on activation records)")
    if malformed:
        print("  malformed: %d" % malformed)


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
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "rotated/older outcome file(s), nearest-newest first (e.g. "
            "--outcome2 f.1 --outcome2 f.2); each may repeat. The canonical "
            "history is the live file first, then each file in the order "
            "given, and every adjacent pair is checked as a rotation "
            "boundary. Order is used as given and is not checked against "
            "the numeric suffixes: listing .2 before .1 yields a "
            "meaningless break on every pair. Default: none."
        ),
    )
    parser.add_argument(
        "--skill-events",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "skill-activation records (JSONL); may repeat. Adapter 'opencode' "
            "reads tool_use lines with part.tool == 'skill' and takes "
            "part.state.input.id as the skill name; adapter 'json' reads flat "
            "{sessionID, skill, ts} lines. Default: none."
        ),
    )
    parser.add_argument(
        "--adapter",
        choices=("opencode", "json"),
        default="opencode",
        help="shape of --skill-events records (default: opencode)",
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
    rotated_paths = list(args.outcome2 or [])
    rotated_records = []
    rotated_malformed = 0
    for rotated_path in rotated_paths:
        file_records, file_malformed = read_jsonl(rotated_path)
        rotated_records.extend(file_records)
        rotated_malformed += file_malformed

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
    for offset, rotated_path in enumerate(rotated_paths):
        print("outcome file %d (rotated/older): %s" % (offset + 2, rotated_path))
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
    if rotated_paths:
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
    if rotated_paths:
        if len(rotated_paths) == 1:
            rotated_breaks, rotated_checked = chain_breaks_per_file(rotated_paths[0])
            if rotated_checked:
                print(
                    "Rotated-outcome chain (`prev`, mid-file): %d break(s) over %d checked link(s)"
                    % (rotated_breaks, rotated_checked)
                )
            else:
                print("Rotated-outcome chain (`prev`, mid-file): no `prev`-bearing records checked")
        else:
            for offset, rotated_path in enumerate(rotated_paths):
                rotated_breaks, rotated_checked = chain_breaks_per_file(rotated_path)
                if rotated_checked:
                    print(
                        "Rotated-outcome chain %d (%s) (`prev`, mid-file): %d break(s) over %d checked link(s)"
                        % (offset + 1, os.path.basename(rotated_path),
                           rotated_breaks, rotated_checked)
                    )
                else:
                    print(
                        "Rotated-outcome chain %d (%s) (`prev`, mid-file): no `prev`-bearing records checked"
                        % (offset + 1, os.path.basename(rotated_path))
                    )
        if len(rotated_paths) == 1:
            status, live_first_prev, rotated_last_hash = boundary_check(
                args.outcome, rotated_paths[0]
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
        else:
            for index, (newer, older, status, newer_prev, older_hash) in enumerate(
                boundary_chain(args.outcome, rotated_paths), start=1
            ):
                label = "Rotation boundary %d (%s vs %s):" % (index, newer, older)
                if status == "match":
                    print("%s cross-file chain INTACT" % (label,))
                elif status == "break":
                    print(
                        "%s break — %s does not match %s (reported as a boundary "
                        "break, not an error)"
                        % (
                            label,
                            str(newer_prev)[:8] + "..." if newer_prev is not None else "<none>",
                            str(older_hash)[:8] + "..." if older_hash is not None else "<none>",
                        )
                    )
                elif status == "absent-rotated":
                    print("%s older file missing or empty — no boundary checked" % (label,))
                elif status == "absent-live":
                    print("%s newer file missing — no boundary checked" % (label,))
                else:  # no-prev
                    print(
                        "%s no `prev`-bearing record in the newer file — no boundary checked"
                        % (label,)
                    )
    print("")
    report_skill_events(args.skill_events, args.adapter)
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
