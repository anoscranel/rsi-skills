#!/usr/bin/env python3
"""Score hit / miss / false-fire for a labeled task set against observed runs.

Implements the mechanical half (steps 3-4) of the miss-rate protocol in
docs/MISS-RATE.md. The labels are the denominator: tasks that NEEDED a skill,
which no activation log can supply. This script never creates or edits labels;
it only scores them and pins the label set's sha256 so any relabel is detectable.

Classification (precise rule, per Decision 3 / Task A):
  hit        fired_skill == expected_skill
  false-fire fired_skill is non-null and != expected_skill
  miss       fired_skill is null (nothing fired)
  unrun      no run row exists for the labeled task_id (counted, never dropped)

Note: MISS-RATE.md step 3 words hit as "fired AND helped"; the binding Task A
rule classifies on fired_skill alone. The optional `helped` field is validated
but does not alter classification. Fractions use N = all labeled tasks,
including unrun ones.

Inputs:
  --labels JSONL  each line {task_id, prompt, expected_skill, label_status,
                             confidence, rationale}
  --runs   JSONL  each line {task_id, fired_skill (string|null), helped (bool,
                             optional)}

Usage:
  python3 miss-rate.py --labels PATH --runs PATH
  python3 miss-rate.py --self-test

Exit codes: 0 report produced, 2 missing/unreadable/invalid input,
3 duplicate task_id in the labels file.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile


class InputError(Exception):
    """Missing, unreadable, or malformed input (exit 2)."""


class DuplicateLabelError(Exception):
    """Duplicate task_id in the labels file (exit 3)."""


def _read_jsonl(path, kind):
    if not os.path.isfile(path):
        raise InputError("%s file not found: %s" % (kind, path))
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise InputError("%s file unreadable: %s (%s)" % (kind, path, exc))
    records = []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError as exc:
            raise InputError("%s line %d: invalid JSON (%s)" % (kind, lineno, exc))
        if not isinstance(obj, dict):
            raise InputError("%s line %d: expected a JSON object" % (kind, lineno))
        records.append(obj)
    return raw, records


def load_labels(path):
    """Return (records, sha256_hex). Raises on duplicates or missing fields."""
    raw, records = _read_jsonl(path, "labels")
    seen = set()
    for rec in records:
        task_id = rec.get("task_id")
        expected = rec.get("expected_skill")
        if not isinstance(task_id, str) or not task_id:
            raise InputError("labels: every row needs a non-empty string task_id")
        if not isinstance(expected, str) or not expected:
            raise InputError("labels: task %s needs a non-empty string expected_skill" % task_id)
        if task_id in seen:
            raise DuplicateLabelError("labels: duplicate task_id %r" % task_id)
        seen.add(task_id)
    return records, hashlib.sha256(raw).hexdigest()


def load_runs(path):
    """Return {task_id: run}. Duplicate run task_ids make the input ambiguous."""
    _, records = _read_jsonl(path, "runs")
    runs = {}
    for rec in records:
        task_id = rec.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise InputError("runs: every row needs a non-empty string task_id")
        fired = rec.get("fired_skill", None)
        if fired is not None and not isinstance(fired, str):
            raise InputError("runs: task %s fired_skill must be a string or null" % task_id)
        helped = rec.get("helped", None)
        if helped is not None and not isinstance(helped, bool):
            raise InputError("runs: task %s helped must be a bool when present" % task_id)
        if task_id in runs:
            raise InputError("runs: duplicate task_id %r (ambiguous observation)" % task_id)
        runs[task_id] = rec
    return runs


def classify(labels, runs):
    """Return (counts, per_task). counts keys: hit, miss, false-fire, unrun."""
    counts = {"hit": 0, "miss": 0, "false-fire": 0, "unrun": 0}
    per_task = []
    for rec in labels:
        task_id = rec["task_id"]
        expected = rec["expected_skill"]
        if task_id not in runs:
            state = "unrun"
        else:
            fired = runs[task_id].get("fired_skill", None)
            if fired == expected:
                state = "hit"
            elif fired is None:
                state = "miss"
            else:
                state = "false-fire"
        counts[state] += 1
        per_task.append({"task_id": task_id, "state": state})
    return counts, per_task


def format_report(labels_path, labels_sha, counts, n):
    lines = [
        "labels: %s" % labels_path,
        "labels_sha256: %s" % labels_sha,
        "N: %d" % n,
    ]
    for state in ("hit", "miss", "false-fire", "unrun"):
        frac = (counts[state] / float(n)) if n else 0.0
        lines.append("%s: %d (%.4f)" % (state, counts[state], frac))
    return "\n".join(lines)


def score(labels_path, runs_path):
    """Produce the report text. Raises InputError / DuplicateLabelError."""
    labels, labels_sha = load_labels(labels_path)
    runs = load_runs(runs_path)
    counts, _ = classify(labels, runs)
    return format_report(labels_path, labels_sha, counts, len(labels))


def self_test():
    """Internal synthetic fixture: 3 tasks, one hit, one miss, one false-fire."""
    labels = [
        {"task_id": "t1", "prompt": "p1", "expected_skill": "skill-a",
         "label_status": "synthetic", "confidence": "high", "rationale": "fixture"},
        {"task_id": "t2", "prompt": "p2", "expected_skill": "skill-b",
         "label_status": "synthetic", "confidence": "high", "rationale": "fixture"},
        {"task_id": "t3", "prompt": "p3", "expected_skill": "skill-c",
         "label_status": "synthetic", "confidence": "high", "rationale": "fixture"},
    ]
    runs = [
        {"task_id": "t1", "fired_skill": "skill-a"},
        {"task_id": "t2", "fired_skill": None},
        {"task_id": "t3", "fired_skill": "skill-z"},
    ]
    tmp = tempfile.mkdtemp(prefix="miss-rate-self-test-")
    try:
        labels_path = os.path.join(tmp, "labels.jsonl")
        runs_path = os.path.join(tmp, "runs.jsonl")
        with open(labels_path, "w") as handle:
            for rec in labels:
                handle.write(json.dumps(rec) + "\n")
        with open(runs_path, "w") as handle:
            for rec in runs:
                handle.write(json.dumps(rec) + "\n")
        report = score(labels_path, runs_path)
        expected_counts = {"hit": 1, "miss": 1, "false-fire": 1, "unrun": 0}
        counts, per_task = classify(labels, load_runs(runs_path))
        assert counts == expected_counts, "counts %r != %r" % (counts, expected_counts)
        assert [t["state"] for t in per_task] == ["hit", "miss", "false-fire"], per_task
        assert "N: 3" in report, report
        assert "hit: 1 (0.3333)" in report, report
        assert "miss: 1 (0.3333)" in report, report
        assert "false-fire: 1 (0.3333)" in report, report
        assert "unrun: 0 (0.0000)" in report, report
        assert "labels_sha256: " in report, report
        print("PASS")
        return 0
    except (AssertionError, InputError, DuplicateLabelError) as exc:
        print("FAIL: %s" % exc)
        return 1
    finally:
        for name in ("labels.jsonl", "runs.jsonl"):
            try:
                os.unlink(os.path.join(tmp, name))
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score miss rate (protocol steps 3-4).")
    parser.add_argument("--labels", help="JSONL label set (task_id, expected_skill, ...)")
    parser.add_argument("--runs", help="JSONL observed runs (task_id, fired_skill, helped?)")
    parser.add_argument("--self-test", action="store_true", help="run the internal synthetic fixture")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.labels or not args.runs:
        parser.error("--labels and --runs are required (or use --self-test)")
    try:
        report = score(args.labels, args.runs)
    except DuplicateLabelError as exc:
        sys.stderr.write("%s\n" % exc)
        return 3
    except InputError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
