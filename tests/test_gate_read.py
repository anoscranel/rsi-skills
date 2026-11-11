#!/usr/bin/env python3
"""Contract tests for scripts/gate-read.py (stdlib unittest only).

Fixtures are built inside a tempfile.mkdtemp() per test and removed in
tearDown; nothing is written into the repo. Every assertion targets a string
the reader actually prints. Run from the repo root:

    python3 -m unittest discover -s tests -v
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READER = os.path.join(REPO_ROOT, "scripts", "gate-read.py")


def render(record):
    """The exact line text the reader will hash (no trailing newline)."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class GateReadCase(unittest.TestCase):
    """Base: a per-test scratch dir, a run() helper, and a JSONL writer."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gate-read-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.tmp, name)

    def write_jsonl(self, name, records, chain=False, break_at=None):
        """Write records as JSONL. With chain=True each record after the
        first carries `prev` = sha256 of the previous rendered line; index
        `break_at` (if given) gets a deliberately wrong `prev` instead."""
        lines = []
        for index, record in enumerate(records):
            record = dict(record)
            if chain and index > 0:
                if index == break_at:
                    record["prev"] = "0" * 64
                else:
                    record["prev"] = sha256_text(lines[index - 1])
            lines.append(render(record))
        target = self.path(name)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return target

    def run_reader(self, *args):
        return subprocess.run(
            [sys.executable, READER] + list(args),
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def assert_in(self, needle, haystack):
        self.assertIn(needle, haystack, "missing %r in output:\n%s" % (needle, haystack))


class TestGateReadContract(GateReadCase):
    # 1
    def test_missing_files_report_zero(self):
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"),
            "--outcome", self.path("no-outcome.jsonl"),
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("0 events (no leaf records found)", result.stdout)
        self.assert_in("Leaf events (total): 0", result.stdout)
        self.assert_in("Outcome records (total): 0", result.stdout)
        self.assert_in("STATUS: GATE NOT EVALUABLE", result.stdout)

    # 2
    def test_join_rate_and_denominator(self):
        leaf = self.write_jsonl("leaf.jsonl", [
            {"sessionID": "s%d" % i, "callID": "c%d" % i, "skill": "ac-%d" % i}
            for i in (1, 2, 3)
        ])
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s%d" % i, "callID": c, "trust": "untrusted"}
            for i, c in ((1, "c1"), (2, "c2"), (9, "c9"))
        ])
        result = self.run_reader("--leaf", leaf, "--outcome", outcome)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("Join rate: 2/3 matched (66.67%)", result.stdout)
        self.assert_in("  ac-1: 1", result.stdout)
        self.assert_in("  ac-2: 1", result.stdout)
        self.assert_in("  ac-3: 1", result.stdout)
        self.assert_in("Unmatched leaf events (joinable, no outcome): 1", result.stdout)

    # 3
    def test_midfile_chain_break(self):
        outcome = self.write_jsonl(
            "outcome.jsonl",
            [
                {"sessionID": "s1", "callID": "c1"},
                {"sessionID": "s1", "callID": "c2"},
                {"sessionID": "s1", "callID": "c3"},
            ],
            chain=True,
            break_at=2,
        )
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"), "--outcome", outcome
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in(
            "Live-outcome chain (`prev`, mid-file): 1 break(s) over 2 checked link(s)",
            result.stdout,
        )

    # 4
    def test_boundary_break_labeled(self):
        rotated = self.write_jsonl("outcome.jsonl.1", [
            {"sessionID": "s0", "callID": "c0"},
        ])
        live = self.write_jsonl(
            "outcome.jsonl",
            [{"sessionID": "s1", "callID": "c1"}, {"sessionID": "s1", "callID": "c2"}],
            chain=True,
        )
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"),
            "--outcome", live, "--outcome2", rotated,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("Rotation boundary: boundary break", result.stdout)
        self.assert_in("reported as a boundary break, not an error", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    # 5
    def test_boundary_intact(self):
        rotated_line = render({"sessionID": "s0", "callID": "c0"})
        rotated = self.path("outcome.jsonl.1")
        with open(rotated, "w", encoding="utf-8") as handle:
            handle.write(rotated_line + "\n")
        live = self.path("outcome.jsonl")
        with open(live, "w", encoding="utf-8") as handle:
            handle.write(render({
                "sessionID": "s1",
                "callID": "c1",
                "prev": sha256_text(rotated_line),
            }) + "\n")
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"),
            "--outcome", live, "--outcome2", rotated,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("Rotation boundary: cross-file chain INTACT", result.stdout)

    # 6
    def test_duplicate_keys(self):
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
        ])
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"), "--outcome", outcome,
            "--outcome2", self.write_jsonl("outcome.jsonl.1", [
                {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
            ]),
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("duplicate keys: 1 of 4 outcome keys", result.stdout)

    # 7
    def test_window_flags(self):
        leaf = self.write_jsonl("leaf.jsonl", [
            {"sessionID": "s1", "callID": "c1", "skill": "ac-a",
             "ts": "2026-11-11T00:00:00+00:00"},
            {"sessionID": "s2", "callID": "c2", "skill": "ac-b",
             "ts": "2026-01-01T00:00:00+00:00"},
        ])
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted",
             "ts": "2026-11-11T00:00:00+00:00"},
            {"sessionID": "s3", "callID": "c3", "trust": "untrusted",
             "ts": "2026-01-01T00:00:00+00:00"},
        ])
        rotated = self.write_jsonl("outcome.jsonl.1", [
            {"sessionID": "s4", "callID": "c4", "trust": "trusted",
             "ts": "2026-01-01T00:00:00+00:00"},
        ])
        result = self.run_reader(
            "--leaf", leaf, "--outcome", outcome,
            "--outcome2", rotated,
            "--since", "2026-11-10T00:00:00",
            "--until", "2026-11-12T00:00:00",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("window: since=", result.stdout)
        self.assert_in(
            "window excluded: 1 leaf, 1 live-outcome, 1 rotated-outcome record(s)",
            result.stdout,
        )
        self.assert_in("Leaf events (total): 1", result.stdout)
        self.assert_in("Outcome records (total): 1", result.stdout)
        self.assert_in("Join rate: 1/1 matched (100.00%)", result.stdout)

    # 8
    def test_validator_verdict_absent_zero(self):
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
        ])
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"), "--outcome", outcome
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("validator_verdict: 0 present", result.stdout)
        self.assert_in("0 present (recorder does not write this field)", result.stdout)

    # 8b
    def test_validator_verdict_present_tally(self):
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s1", "callID": "c1", "validator_verdict": "pass"},
            {"sessionID": "s2", "callID": "c2", "validator_verdict": "fail"},
            {"sessionID": "s3", "callID": "c3", "validator_verdict": ""},
        ])
        result = self.run_reader(
            "--leaf", self.path("no-leaf.jsonl"), "--outcome", outcome
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("validator_verdict: 3 present", result.stdout)

    # 9
    def test_writes_nothing(self):
        leaf = self.write_jsonl("leaf.jsonl", [
            {"sessionID": "s1", "callID": "c1", "skill": "ac-a"},
        ])
        outcome = self.write_jsonl("outcome.jsonl", [
            {"sessionID": "s1", "callID": "c1", "trust": "untrusted"},
        ], chain=True)
        rotated = self.write_jsonl("outcome.jsonl.1", [
            {"sessionID": "s0", "callID": "c0"},
        ])

        def snapshot(root):
            entries = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort()
                for name in sorted(filenames):
                    full = os.path.join(dirpath, name)
                    entries.append((
                        os.path.relpath(full, root),
                        os.path.getsize(full),
                    ))
            return entries

        before_tmp = snapshot(self.tmp)
        before_repo = snapshot(REPO_ROOT)
        result = self.run_reader(
            "--leaf", leaf, "--outcome", outcome, "--outcome2", rotated
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(snapshot(self.tmp), before_tmp)
        self.assertEqual(snapshot(REPO_ROOT), before_repo)

    # 10
    def test_help_exits_zero(self):
        result = self.run_reader("--help")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_in("--outcome2", result.stdout)
        self.assert_in("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
