#!/usr/bin/env python3
"""Emit leaf records from an opencode session store, per the schema attribution rule.

READ-ONLY by construction: the session database is opened with mode=ro and the only
output is appended to the leaf log (or stdout with --dry-run).

Why this exists: an in-process harness writer can never produce an independent leaf
record. The plugin that records outcomes holds only the *routing* call's id, so using
it reproduces the vacuous join that SPEC section-0 refuses. This observer instead reads
the session store and attributes each skill activation to a DIFFERENT call -- the first
tool call the skill issued after activation -- and writes callID: null when it issued none.

The rule is an inference, not a measurement. See the schema, "Attribution rule".

Usage:
  python3 skill-observer.py --db PATH [--out PATH] [--since ISO] [--dry-run]

Exit codes: 0 report produced, 2 argument error, 3 database unreadable.
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_DB = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db"
)
DEFAULT_OUT = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode", "rsi", "leaf-events.jsonl"
)


def iso_to_ms(value):
    """Accept ISO-8601 (with or without Z) or a plain date; return epoch ms."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError("not ISO-8601: %r" % value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def ms_to_iso(ms):
    return (
        datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def fetch_activations(conn, cutoff_ms):
    """Yield (session_id, activation_seq, skill, activation_call_id, model, ts_ms)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, seq, data
        FROM session_message
        WHERE type = 'assistant' AND time_created > ?
        ORDER BY session_id, seq
        """,
        (cutoff_ms,),
    )
    for session_id, seq, blob in cursor:
        try:
            payload = json.loads(blob)
        except ValueError:
            continue
        model = (payload.get("model") or {}).get("id")
        for part in payload.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") != "tool" or part.get("name") != "skill":
                continue
            state = part.get("state") or {}
            skill = (state.get("input") or {}).get("id")
            if not isinstance(skill, str) or not skill:
                continue
            yield (
                session_id,
                seq,
                skill,
                part.get("id"),
                model,
                (payload.get("time") or {}).get("created"),
            )


def build_records(conn, cutoff_ms):
    """Apply the attribution rule; return (records, stats).

    A call id claimed by more than one skill cannot be evidence for either of them, so
    collisions are downgraded to callID: null (an honest miss) rather than left to
    inflate the join rate. Measured 2026-11-12 (earlier same-day probe window, pre-influx): 8 of 100 distinct ids were shared."""
    activations = list(fetch_activations(conn, cutoff_ms))
    by_session = {}
    for record in activations:
        by_session.setdefault(record[0], [])

    cursor = conn.cursor()
    records = []
    joined = 0
    unjoined = 0
    for session_id, seq, skill, activation_call_id, model, ts_ms in activations:
        cursor.execute(
            """
            SELECT data FROM session_message
            WHERE session_id = ? AND seq > ? AND type = 'assistant'
            ORDER BY seq LIMIT 40
            """,
            (session_id, seq),
        )
        attributed = None
        for (blob,) in cursor:
            try:
                payload = json.loads(blob)
            except ValueError:
                continue
            for part in payload.get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "tool":
                    continue
                if part.get("id") == activation_call_id:
                    continue
                # Only a tool call counts as the leaf's own work. Without this guard a
                # later skill ACTIVATION would be taken as the attribution, silently
                # swapping one skill's evidence onto another (measured: happened live).
                if part.get("name") == "skill":
                    continue
                attributed = part.get("id")
                break
            if attributed:
                break

        records.append(
            {
                "ts": ms_to_iso(ts_ms) if isinstance(ts_ms, int) else None,
                "skill": skill,
                "leaf_routed": None,
                "trigger_text": None,
                "model": model,
                "sessionID": session_id,
                "callID": attributed if attributed != activation_call_id else None,
            }
        )

    # Collision downgrade: one call id cannot stand as evidence for two skills.
    claims = {}
    for record in records:
        if record["callID"]:
            claims.setdefault(record["callID"], set()).add(record["skill"])
    collisions = {cid for cid, skills in claims.items() if len(skills) > 1}
    for record in records:
        if record["callID"] in collisions:
            record["callID"] = None

    joined = sum(1 for r in records if r["callID"])
    unjoined = len(records) - joined
    stats = {
        "activations": len(activations),
        "joined": joined,
        "unjoined": unjoined,
        "sessions": len(by_session),
        "collisions": len(collisions),
    }
    return records, stats


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Emit leaf records from an opencode session store using the schema's "
            "attribution rule. Read-only on the database; appends to the leaf log."
        )
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="session store path")
    parser.add_argument("--out", default=DEFAULT_OUT, help="leaf-events.jsonl path")
    parser.add_argument(
        "--since",
        default=None,
        help="ISO-8601 lower bound on activation time (default: 14 days)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print records to stdout; write nothing",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.db):
        print("error: session store not found: %s" % args.db, file=sys.stderr)
        return 3
    try:
        cutoff = (
            iso_to_ms(args.since)
            if args.since
            else int(
                (datetime.now(tz=timezone.utc) - timedelta(days=14)).timestamp() * 1000
            )
        )
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    try:
        conn = sqlite3.connect("file:%s?mode=ro" % args.db, uri=True, timeout=30)
    except sqlite3.Error as exc:
        print("error: cannot open store read-only: %s" % exc, file=sys.stderr)
        return 3

    try:
        records, stats = build_records(conn, cutoff)
    except sqlite3.Error as exc:
        print("error: query failed: %s" % exc, file=sys.stderr)
        return 3
    finally:
        conn.close()

    if args.dry_run:
        for record in records:
            print(json.dumps(record, sort_keys=True))
    else:
        parent = os.path.dirname(args.out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, "a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    joined_rate = (
        "%.1f%%" % (100.0 * stats["joined"] / stats["activations"])
        if stats["activations"]
        else "n/a"
    )
    print(
        "skill activations: %d across %d session(s)"
        % (stats["activations"], stats["sessions"]),
        file=sys.stderr,
    )
    print(
        "attributed to a later call: %d | unjoinable (callID null): %d | %s"
        % (stats["joined"], stats["unjoined"], joined_rate),
        file=sys.stderr,
    )
    if stats["collisions"]:
        print(
            "downgraded to null (call id claimed by >1 skill): %d"
            % stats["collisions"],
            file=sys.stderr,
        )
    print(
        "NOTE: this rate is a LOWER BOUND on fired-leaf success, not the rate itself "
        "(reasoning-only leaves are indistinguishable from idle ones).",
        file=sys.stderr,
    )
    print(
        "STATUS: OBSERVER RECORDS, GATE NOT EVALUATED (see SPEC section 0)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
