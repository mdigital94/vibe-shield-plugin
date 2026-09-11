import ast
from pathlib import Path
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class DependencyTemplateTests(unittest.TestCase):
    def run_template(self, paths):
        source = (ROOT / 'templates/security-ci.yml').read_text()
        code = textwrap.dedent(source.split("python3 - <<'PY_AUDIT'\n", 1)[1].rsplit('          PY_AUDIT', 1)[0])
        ast.parse(code)
        with mock.patch('subprocess.check_output', return_value=('\0'.join(paths) + '\0').encode()):
            with mock.patch('subprocess.run') as run:
                exec(compile(code, 'security-ci.yml', 'exec'), {})
                return run.call_args_list

    def test_npm_subproject_actually_runs_scanner_at_moderate_threshold(self):
        calls = self.run_template(['apps/site/package.json', 'apps/site/package-lock.json'])
        self.assertEqual(calls[0].args[0], ['npm', 'audit', '--audit-level=moderate'])
        self.assertTrue(str(calls[0].kwargs['cwd']).endswith('apps/site'))

    def test_pnpm_cannot_silently_skip_dependency_audit(self):
        with self.assertRaises(SystemExit) as error:
            self.run_template(['package.json', 'pnpm-lock.yaml'])
        self.assertEqual(error.exception.code, 1)

    def test_pyproject_cannot_silently_skip_dependency_audit(self):
        with self.assertRaises(SystemExit) as error:
            self.run_template(['app/pyproject.toml'])
        self.assertEqual(error.exception.code, 1)

    def test_workspace_package_is_covered_by_ancestor_lock(self):
        calls = self.run_template(['package.json', 'package-lock.json', 'packages/ui/package.json'])
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
