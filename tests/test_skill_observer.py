"""Contract tests for scripts/skill-observer.py.

Stdlib unittest only, no network, no writes outside a temp dir. Fixtures are built as a
minimal SQLite database with the two tables the observer reads, so the tests do not need
the real (multi-gigabyte) session store.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBSERVER = os.path.join(REPO_ROOT, "scripts", "skill-observer.py")


def message(session_id, seq, created_ms, parts, model="test-model"):
    return (
        session_id,
        seq,
        created_ms,
        json.dumps({"time": {"created": created_ms}, "model": {"id": model}, "content": parts}),
    )


def tool_part(part_id, name, skill_id=None, status="completed"):
    state = {"status": status, "input": {}}
    if skill_id:
        state["input"]["id"] = skill_id
    return {"type": "tool", "id": part_id, "name": name, "state": state}


class ObserverContract(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="observer-test-")
        self.db = os.path.join(self.dir, "session.db")
        self.out = os.path.join(self.dir, "leaf-events.jsonl")
        conn = sqlite3.connect(self.db)
        conn.execute(
            "CREATE TABLE session_message (id text, session_id text, type text,"
            " seq integer, time_created integer, time_updated integer, data text)"
        )
        self.conn = conn

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)

    def insert(self, rows):
        self.conn.executemany(
            "INSERT INTO session_message (session_id, seq, time_created, data, type)"
            " VALUES (?,?,?,?,'assistant')",
            rows,
        )
        self.conn.commit()

    def run_observer(self, *args):
        return subprocess.run(
            [sys.executable, OBSERVER, "--db", self.db, "--dry-run"] + list(args),
            capture_output=True,
            text=True,
            timeout=120,
        )

    # 1 — the attribution rule: activation then a later tool call
    def test_attributes_to_later_call(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["skill"], "ac-alpha")
        self.assertEqual(records[0]["callID"], "call-B")
        self.assertEqual(records[0]["model"], "test-model")
        self.assertIsNone(records[0]["leaf_routed"])

    # 2 — never the activation's own id (the vacuous join)
    def test_never_uses_activation_id(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        # Pin the exact value: a mutation that falls back to the activation's own id
        # would still satisfy a bare inequality if it attributed nothing at all.
        self.assertEqual(records[0]["callID"], "call-B")
        self.assertNotEqual(records[0]["callID"], "call-A")

    # 2b — the guard that matters: the activation's id reappearing in a LATER message
    def test_skips_repeated_activation_id(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            # the same call id streamed again in a later message
            message("S1", 2, 1700000001000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 3, 1700000002000, [tool_part("call-B", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertEqual(record["callID"], "call-B")

    # 3 — a skill that issued no tool call is an honest miss
    def test_no_later_call_is_null(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["callID"])

    # 4 — collision downgrade: one call id cannot evidence two skills
    def test_collision_downgraded_to_null(self):
        self.insert([
            message("S1", 1, 1700000000000, [
                tool_part("call-A", "skill", "ac-alpha"),
                tool_part("call-B", "skill", "ac-beta"),
            ]),
            message("S1", 2, 1700000001000, [tool_part("call-C", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r["callID"] is None for r in records))
        self.assertIn("downgraded to null", result.stderr)

    # 5 — a later ACTIVATION must never be taken as the leaf's own work
    def test_skips_later_activation_as_attribution(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "skill", "ac-beta")]),
            message("S1", 3, 1700000002000, [tool_part("call-C", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 2)
        # ac-alpha: call-B is an activation, not its own work, so the first eligible
        # call is call-C. ac-beta: same target, but the collision downgrade applies,
        # so both land on null rather than letting one id evidence two skills.
        self.assertEqual([r["callID"] for r in records], [None, None])
        self.assertIn("downgraded to null", result.stderr)

    # 5b — non-skill tools are not activations
    def test_ignores_non_skill_tools(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "shell")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "read")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        self.assertEqual(result.stdout.strip(), "")
        self.assertIn("skill activations: 0", result.stderr)

    # 6 — lower bound wording is never dropped
    def test_states_lower_bound(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        self.assertIn("LOWER BOUND", result.stderr)
        self.assertIn("GATE NOT EVALUATED", result.stderr)

    # 7 — missing database is an error, not a crash or a false success
    def test_missing_db_exit_3(self):
        result = subprocess.run(
            [sys.executable, OBSERVER, "--db", os.path.join(self.dir, "nope.db"), "--dry-run"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("not found", result.stderr)

    # 8 — window excludes older activations
    def test_since_excludes_older(self):
        self.insert([
            message("S1", 1, 1600000000000, [tool_part("call-A", "skill", "ac-old")]),
            message("S1", 2, 1700000000000, [tool_part("call-B", "skill", "ac-new")]),
            message("S1", 3, 1700000001000, [tool_part("call-C", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual([r["skill"] for r in records], ["ac-new"])

    # 9 — the database is opened read-only: the file must be unchanged
    def test_database_not_modified(self):
        self.insert([
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-B", "shell")]),
        ])
        self.conn.close()
        before = os.stat(self.db).st_mtime_ns, os.path.getsize(self.db)
        result = self.run_observer("--since", "2023-11-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        after = os.stat(self.db).st_mtime_ns, os.path.getsize(self.db)
        self.assertEqual(before, after)

    # 10 — malformed JSON rows are skipped, not fatal
    def test_malformed_row_skipped(self):
        self.insert([
            ("S1", 1, 1700000000000, "{not json"),
            message("S1", 2, 1700000001000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 3, 1700000002000, [tool_part("call-B", "shell")]),
        ])
        result = self.run_observer("--since", "2023-11-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(records), 1)

    # 13 — never-own-id, non-skill shape: a harness that re-streams the
    # activation id as a NON-skill tool part (name mutates across part
    # states; the schema's producer list is harness-generic). The observer
    # must attribute to the later call, never to the re-streamed id.
    def test_never_own_id_non_skill_restream(self):
        rows = [
            message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")]),
            message("S1", 2, 1700000001000, [tool_part("call-A", "read")]),
            message("S1", 3, 1700000002000, [tool_part("call-C", "write")]),
        ]
        self.insert(rows)
        records = self.run_and_collect()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["callID"], "call-C")
        self.assertEqual(records[0]["skill"], "ac-alpha")

    # 14 — the 40-message window: an eligible call beyond it must not be
    # attributed (the observer's scan is bounded; beyond it, callID null).
    def test_window_is_bounded_at_40(self):
        rows = [message("S1", 1, 1700000000000, [tool_part("call-A", "skill", "ac-alpha")])]
        for i in range(2, 46):  # rows at seq 2..45: plain assistant text, nothing eligible
            rows.append(message("S1", i, 1700000000000 + i * 1000, []))
        rows.append(message("S1", 46, 1700000046000, [tool_part("call-Z", "write")]))
        self.insert(rows)
        records = self.run_and_collect()
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["callID"])

    # 15 — same-row sibling: a non-skill tool part sharing the activation
    # row must not be attributed (seq anchor is strictly greater).
    def test_same_row_sibling_not_attributed(self):
        rows = [
            message("S1", 1, 1700000000000, [
                tool_part("call-A", "skill", "ac-alpha"),
                tool_part("call-X", "shell"),
            ]),
        ]
        self.insert(rows)
        records = self.run_and_collect()
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["callID"])

    def run_and_collect(self):
        result = self.run_observer("--since", "2023-11-01")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.strip().startswith("{")
        ]


if __name__ == "__main__":
    unittest.main()
