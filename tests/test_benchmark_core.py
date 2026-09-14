"""Behavioral checks for authored, inert benchmark fixtures; never execute model output."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


CASES = json.loads((Path(__file__).resolve().parents[1] / "benchmarks" / "cases_core.json").read_text())


def implementation(family, variant):
    case = next(case for case in CASES if case["family"] == family and case["variant"] == variant)
    namespace = {"__name__": "benchmark_fixture"}
    exec(compile(case["files"]["app.py"], case["id"] + "/app.py", "exec"), namespace)
    return namespace


class CoreBenchmarkTests(unittest.TestCase):
    def test_case_pairs_and_ground_truth_point_to_source(self):
        self.assertEqual([case["id"] for case in CASES], ["c%02d" % n for n in range(1, 13)])
        families = {case["family"] for case in CASES}
        self.assertEqual(len(families), 6)
        for family in families:
            pair = [case for case in CASES if case["family"] == family]
            self.assertEqual({case["variant"] for case in pair}, {"vulnerable", "safe"})
        for case in CASES:
            self.assertTrue(case["scope"])
            self.assertEqual(len(case["expected"]), int(case["variant"] == "vulnerable"))
            for finding in case["expected"]:
                lines = case["files"][finding["file"]].splitlines()
                self.assertGreaterEqual(finding["line_start"], 1)
                self.assertLessEqual(finding["line_start"], finding["line_end"])
                self.assertLessEqual(finding["line_end"], len(lines))
                self.assertTrue(lines[finding["line_start"] - 1].strip())

    def test_sql_input_can_expand_results_only_in_vulnerable_case(self):
        vulnerable = implementation("sql_injection", "vulnerable")["lookup"]
        safe = implementation("sql_injection", "safe")["lookup"]
        self.assertEqual(vulnerable("alice"), safe("alice"))
        self.assertEqual(len(vulnerable("' OR 1=1 --")), 2)
        self.assertEqual(safe("' OR 1=1 --"), [])

    def test_record_owner_is_enforced_in_safe_case(self):
        vulnerable = implementation("idor", "vulnerable")["read_record"]
        safe = implementation("idor", "safe")["read_record"]
        self.assertEqual(vulnerable("alice", 1), safe("alice", 1))
        self.assertEqual(vulnerable("alice", 2), "draft-b")
        with self.assertRaises(PermissionError):
            safe("alice", 2)

    def test_paths_cannot_escape_safe_root(self):
        vulnerable = implementation("path_traversal", "vulnerable")["select_path"]
        safe = implementation("path_traversal", "safe")["select_path"]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            root = base / "uploads"
            root.mkdir()
            self.assertEqual(safe(root, "note.txt"), root / "note.txt")
            for name in ("../outside.txt", str(base / "outside.txt")):
                self.assertNotIn(root, vulnerable(root, name).resolve().parents)
                with self.assertRaises(ValueError):
                    safe(root, name)
            (root / "link").symlink_to(base, target_is_directory=True)
            with self.assertRaises(ValueError):
                safe(root, "link/outside.txt")

    def test_shell_payload_is_literal_argument_in_safe_case(self):
        payload = "hello; printf injected"
        vulnerable = implementation("shell_injection", "vulnerable")["build_command"](payload)
        safe = implementation("shell_injection", "safe")["build_command"](payload)
        self.assertTrue(vulnerable["shell"])
        self.assertIn("; printf injected", vulnerable["args"])
        self.assertFalse(safe["shell"])
        self.assertEqual(safe["args"], ["printf", "%s", payload])

    def test_password_verifier_uses_independent_salts_and_cost(self):
        password = "fixture-only-input"
        vulnerable = implementation("password_hashing", "vulnerable")["hash_password"]
        safe = implementation("password_hashing", "safe")["hash_password"]
        self.assertEqual(vulnerable(password), hashlib.md5(password.encode()).hexdigest())
        first, second = safe(password), safe(password)
        self.assertNotEqual(first, second)
        for encoded in (first, second):
            algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
            self.assertEqual(algorithm, "scrypt")
            salt = bytes.fromhex(salt_hex)
            self.assertEqual(len(salt), 16)
            self.assertEqual(hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p)).hex(), digest_hex)

    def test_destination_policy_rejects_internal_and_disguised_urls(self):
        vulnerable = implementation("ssrf", "vulnerable")["destination"]
        safe = implementation("ssrf", "safe")["destination"]
        allowed = "https://api.example.invalid/v1/items"
        self.assertEqual(vulnerable(allowed), safe(allowed))
        for url in ("http://127.0.0.1/admin", "http://169.254.169.254/", "http://[::1]/", "https://api.example.invalid.evil.invalid/", "https://api.example.invalid@127.0.0.1/", "https://api.example.invalid:444/", "http://api.example.invalid/"):
            self.assertEqual(vulnerable(url), url)
            with self.assertRaises(ValueError):
                safe(url)


if __name__ == "__main__":
    unittest.main()
