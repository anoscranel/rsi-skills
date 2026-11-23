"""Contract tests for scripts/miss-rate.py.

Stdlib unittest only, no network, no writes outside a temp dir. The scorer is
invoked as a subprocess, matching the house style of test_skill_observer.py.
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
SCORER = os.path.join(REPO_ROOT, "scripts", "miss-rate.py")


def label(task_id, expected_skill):
    return {
        "task_id": task_id,
        "prompt": "synthetic prompt for %s" % task_id,
        "expected_skill": expected_skill,
        "label_status": "synthetic",
        "confidence": "high",
        "rationale": "fixture",
    }


def run_row(task_id, fired_skill, helped=None):
    row = {"task_id": task_id, "fired_skill": fired_skill}
    if helped is not None:
        row["helped"] = helped
    return row


class MissRateContract(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="miss-rate-test-")
        self.labels = os.path.join(self.dir, "labels.jsonl")
        self.runs = os.path.join(self.dir, "runs.jsonl")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_jsonl(self, path, rows):
        with open(path, "w") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    def run_scorer(self, *args):
        return subprocess.run(
            [sys.executable, SCORER] + list(args),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def score(self):
        result = self.run_scorer("--labels", self.labels, "--runs", self.runs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def parse_counts(self, stdout):
        counts = {}
        for line in stdout.splitlines():
            for state in ("hit", "miss", "false-fire", "unrun"):
                if line.startswith(state + ": "):
                    counts[state] = int(line.split(": ")[1].split(" ")[0])
        return counts

    # (a) hit / miss / false-fire classify correctly
    def test_three_states(self):
        self.write_jsonl(self.labels, [
            label("t1", "skill-a"),
            label("t2", "skill-b"),
            label("t3", "skill-c"),
        ])
        self.write_jsonl(self.runs, [
            run_row("t1", "skill-a"),
            run_row("t2", None),
            run_row("t3", "skill-z"),
        ])
        stdout = self.score()
        self.assertEqual(self.parse_counts(stdout),
                         {"hit": 1, "miss": 1, "false-fire": 1, "unrun": 0})
        self.assertIn("N: 3", stdout)
        self.assertIn("hit: 1 (0.3333)", stdout)
        self.assertIn("miss: 1 (0.3333)", stdout)
        self.assertIn("false-fire: 1 (0.3333)", stdout)
        self.assertIn("unrun: 0 (0.0000)", stdout)

    # (a2) helped does not alter classification (Task A precise rule)
    def test_helped_field_does_not_change_hit(self):
        self.write_jsonl(self.labels, [label("t1", "skill-a")])
        self.write_jsonl(self.runs, [run_row("t1", "skill-a", helped=False)])
        stdout = self.score()
        self.assertEqual(self.parse_counts(stdout)["hit"], 1)

    # (b) unrun tasks are counted, not dropped
    def test_unrun_counted_not_dropped(self):
        self.write_jsonl(self.labels, [
            label("t1", "skill-a"),
            label("t2", "skill-b"),
            label("t3", "skill-c"),
        ])
        self.write_jsonl(self.runs, [
            run_row("t1", "skill-a"),
            run_row("t2", None),
        ])
        stdout = self.score()
        self.assertIn("N: 3", stdout)
        counts = self.parse_counts(stdout)
        self.assertEqual(counts["unrun"], 1)
        self.assertEqual(counts["hit"] + counts["miss"] + counts["false-fire"]
                         + counts["unrun"], 3)
        self.assertIn("unrun: 1 (0.3333)", stdout)

    # (c) duplicate task_id in labels -> exit 3
    def test_duplicate_label_exit_3(self):
        self.write_jsonl(self.labels, [
            label("t1", "skill-a"),
            label("t1", "skill-b"),
        ])
        self.write_jsonl(self.runs, [run_row("t1", "skill-a")])
        result = self.run_scorer("--labels", self.labels, "--runs", self.runs)
        self.assertEqual(result.returncode, 3)
        self.assertIn("duplicate task_id", result.stderr)

    # (d) relabel detectability: editing a label changes the pinned hash
    def test_relabel_changes_hash(self):
        rows = [label("t1", "skill-a"), label("t2", "skill-b")]
        self.write_jsonl(self.labels, rows)
        self.write_jsonl(self.runs, [
            run_row("t1", "skill-a"),
            run_row("t2", "skill-b"),
        ])
        first = self.score()
        with open(self.labels, "rb") as handle:
            first_sha = hashlib.sha256(handle.read()).hexdigest()
        self.assertIn("labels_sha256: %s" % first_sha, first)
        # relabel t2: expected skill changes
        rows[1]["expected_skill"] = "skill-z"
        self.write_jsonl(self.labels, rows)
        second = self.score()
        with open(self.labels, "rb") as handle:
            second_sha = hashlib.sha256(handle.read()).hexdigest()
        self.assertNotEqual(first_sha, second_sha)
        self.assertIn("labels_sha256: %s" % second_sha, second)
        # the relabel also flips the classification: t2 was hit, now false-fire
        self.assertEqual(self.parse_counts(first)["hit"], 2)
        self.assertEqual(self.parse_counts(second)["false-fire"], 1)

    # (e) missing input -> exit 2
    def test_missing_labels_exit_2(self):
        self.write_jsonl(self.runs, [run_row("t1", "skill-a")])
        result = self.run_scorer("--labels", os.path.join(self.dir, "nope.jsonl"),
                                 "--runs", self.runs)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr)

    def test_missing_runs_exit_2(self):
        self.write_jsonl(self.labels, [label("t1", "skill-a")])
        result = self.run_scorer("--labels", self.labels,
                                 "--runs", os.path.join(self.dir, "nope.jsonl"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr)

    # (e2) malformed input is an error, not a crash or a false report
    def test_malformed_labels_exit_2(self):
        with open(self.labels, "w") as handle:
            handle.write("{not json\n")
        self.write_jsonl(self.runs, [])
        result = self.run_scorer("--labels", self.labels, "--runs", self.runs)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid JSON", result.stderr)

    def test_duplicate_run_exit_2(self):
        self.write_jsonl(self.labels, [label("t1", "skill-a")])
        self.write_jsonl(self.runs, [
            run_row("t1", "skill-a"),
            run_row("t1", None),
        ])
        result = self.run_scorer("--labels", self.labels, "--runs", self.runs)
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate task_id", result.stderr)

    # empty label set: N=0, no division by zero
    def test_empty_labels(self):
        self.write_jsonl(self.labels, [])
        self.write_jsonl(self.runs, [])
        stdout = self.score()
        self.assertIn("N: 0", stdout)
        self.assertIn("hit: 0 (0.0000)", stdout)

    # the built-in self-test passes as a subprocess
    def test_self_test_pass(self):
        result = self.run_scorer("--self-test")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    # the report pins the labels path
    def test_report_names_labels_path(self):
        self.write_jsonl(self.labels, [label("t1", "skill-a")])
        self.write_jsonl(self.runs, [run_row("t1", "skill-a")])
        stdout = self.score()
        self.assertIn("labels: %s" % self.labels, stdout)


if __name__ == "__main__":
    unittest.main()
