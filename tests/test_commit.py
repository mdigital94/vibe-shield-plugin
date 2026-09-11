import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAKE = 'AKIA' + 'Z9' * 8


class CommitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-shield-commit-')
        self.repo = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.env.pop('VIBE_SHIELD_SKIP', None)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@invalid.test')
        self.git('config', 'core.hooksPath', str(self.repo / 'no-hooks'))
        (self.repo / 'readme.txt').write_text('clean\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env, check=True, capture_output=True).stdout

    def guard(self, command='git commit -m test'):
        result = subprocess.run(['bash', str(ROOT / 'scripts/guard-commit.sh'), command],
                                cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotIn(FAKE, result.stdout + result.stderr)
        return result.returncode

    def test_clean_index_passes(self):
        self.assertEqual(self.guard(), 0)

    def test_staged_secret_blocks_even_with_clean_worktree(self):
        path = self.repo / 'config.txt'
        path.write_text(FAKE)
        self.git('add', 'config.txt')
        path.write_text('clean')
        self.assertEqual(self.guard(), 2)
        self.assertIn(FAKE.encode(), self.git('show', ':config.txt'))

    def test_clean_stage_not_blocked_by_unstaged_secret(self):
        (self.repo / 'readme.txt').write_text(FAKE)
        self.assertEqual(self.guard(), 0)
        self.assertEqual(self.guard('git commit -am test'), 2)

    def test_template_filename_does_not_exempt_content(self):
        path = self.repo / '.env.example'
        path.write_text('API_KEY=<insert-value>\n')
        self.git('add', str(path))
        self.assertEqual(self.guard(), 0)
        path.write_text(FAKE)
        self.git('add', str(path))
        self.assertEqual(self.guard(), 2)

    def test_renamed_file_with_secret_is_scanned(self):
        (self.repo / 'old.txt').write_text(FAKE)
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.git('mv', 'old.txt', 'new.txt')
        self.assertEqual(self.guard(), 2)

    def test_add_glob_scans_new_candidates(self):
        (self.repo / 'new.txt').write_text(FAKE)
        self.assertEqual(self.guard('git add *.txt && git commit -m test'), 2)

    def test_force_add_checks_ignored_candidates(self):
        (self.repo / '.gitignore').write_text('secret.txt\n')
        (self.repo / 'secret.txt').write_text(FAKE)
        self.assertEqual(self.guard('git add -f secret.txt && git commit -m test'), 2)

    def test_quoted_and_newline_paths_cannot_hide_a_secret(self):
        name = 'odd\n"path.txt'
        (self.repo / name).write_text(FAKE)
        self.git('add', name)
        self.assertEqual(self.guard(), 2)

    def test_large_file_not_silently_skipped(self):
        (self.repo / 'big.txt').write_text('safe\n' * 210000 + FAKE)
        self.git('add', 'big.txt')
        self.assertEqual(self.guard(), 2)

    def test_sensitive_name_blocks_without_known_key_format(self):
        (self.repo / '.env').write_text('PASSWORD=something\n')
        self.git('add', '.env')
        self.assertEqual(self.guard(), 2)

    def test_pathspec_commit_checks_worktree(self):
        (self.repo / 'readme.txt').write_text(FAKE)
        self.assertEqual(self.guard('git commit readme.txt -m test'), 2)

    def test_invalid_allowlist_does_not_hide_secret(self):
        (self.repo / '.vibe-shield').mkdir()
        (self.repo / '.vibe-shield/allowlist').write_text('[\n.*\n')
        (self.repo / 'readme.txt').write_text(FAKE)
        self.git('add', 'readme.txt')
        self.assertEqual(self.guard(), 2)


    def scanner(self, *args):
        result = subprocess.run(['bash', str(ROOT / 'scripts/scan-secrets.sh'), *args],
                                cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotIn(FAKE, result.stdout + result.stderr)
        return result

    def test_scanner_distinguishes_clean_findings_and_incomplete(self):
        self.assertEqual(self.scanner().returncode, 0)
        (self.repo / '.env.example').write_text(FAKE)
        self.assertEqual(self.scanner().returncode, 2)
        self.assertEqual(self.scanner('/path/that/does/not/exist').returncode, 3)

    def test_history_scanner_finds_secret_removed_from_current_tree(self):
        (self.repo / 'readme.txt').write_text(FAKE)
        self.git('add', '.')
        self.git('commit', '-qm', 'synthetic fixture')
        (self.repo / 'readme.txt').write_text('clean')
        self.git('add', '.')
        self.git('commit', '-qm', 'clean current version')
        self.assertEqual(self.scanner().returncode, 0)
        self.assertEqual(self.scanner('--history', '--all').returncode, 2)
        self.assertEqual(self.scanner('--history', '1').returncode, 3)

    def test_scanner_reports_secret_with_colon_in_filename_without_value(self):
        (self.repo / 'odd:name.txt').write_text(FAKE)
        self.assertEqual(self.scanner().returncode, 2)

    def test_postwrite_template_scans_actual_content(self):
        import json
        path = self.repo / '.env.example'
        path.write_text(FAKE)
        result = subprocess.run(['bash', str(ROOT / 'scripts/check-write.sh')],
                                input=json.dumps({'cwd': str(self.repo), 'tool_input': {'file_path': str(path)}}),
                                cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(FAKE, result.stdout + result.stderr)


    def test_grouped_force_add_checks_ignored_candidates(self):
        (self.repo / '.gitignore').write_text('ignored.txt\n')
        (self.repo / 'ignored.txt').write_text(FAKE)
        self.assertEqual(self.guard('git add -Af ignored.txt && git commit -m test'), 2)

    def test_shallow_history_never_reports_complete(self):
        with tempfile.TemporaryDirectory(prefix='vibe-shield-shallow-') as folder:
            clone = Path(folder) / 'clone'
            subprocess.run(['git', 'clone', '--quiet', '--depth', '1', self.repo.as_uri(), str(clone)],
                           env=self.env, check=True, capture_output=True)
            result = subprocess.run(['bash', str(ROOT / 'scripts/scan-secrets.sh'), '--history', '--all'],
                                    cwd=clone, env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)

    def test_non_git_generated_directory_is_not_silently_excluded(self):
        with tempfile.TemporaryDirectory(prefix='vibe-shield-nongit-') as folder:
            base = Path(folder)
            (base / 'dist').mkdir()
            (base / 'dist/file.txt').write_text(FAKE)
            self.assertEqual(self.scanner(str(base)).returncode, 2)

    def test_history_scans_unchanged_blob_only_once(self):
        import argparse
        import contextlib
        import io
        import sys
        from unittest import mock
        sys.path.insert(0, str(ROOT / 'scripts'))
        try:
            import secret_scan
        finally:
            sys.path.pop(0)
        for _ in range(3):
            self.git('commit', '--allow-empty', '-qm', 'same contents')
        with mock.patch.object(secret_scan, 'git', wraps=secret_scan.git) as git_spy:
            with contextlib.redirect_stdout(io.StringIO()):
                result = secret_scan.run(argparse.Namespace(target=str(self.repo), history='--all'))
        self.assertEqual(result, 0)
        blob_reads = [call for call in git_spy.call_args_list if call.args[1:3] == ('cat-file', 'blob')]
        self.assertEqual(len(blob_reads), 1)


    def test_history_scanner_includes_commit_and_tag_messages(self):
        self.git('commit', '--allow-empty', '-qm', FAKE)
        self.assertEqual(self.scanner('--history', '--all').returncode, 2)
        self.git('reset', '--hard', 'HEAD~1')
        self.git('tag', '-a', 'synthetic-tag', '-m', FAKE)
        self.assertEqual(self.scanner('--history', '--all').returncode, 2)

    def test_history_scanner_accepts_clean_tree_checkpoint(self):
        tree = self.git('rev-parse', 'HEAD^{tree}').decode().strip()
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.assertEqual(self.scanner('--history', '--all').returncode, 0)

    def test_history_scanner_checks_tree_checkpoint_contents(self):
        (self.repo / 'readme.txt').write_text(FAKE)
        self.git('add', '.')
        tree = self.git('write-tree').decode().strip()
        self.git('reset', '--hard', 'HEAD')
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.assertEqual(self.scanner('--history', '--all').returncode, 2)

    def test_history_checkpoint_submodule_is_incomplete(self):
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '160000,' + commit + ',nested')
        tree = self.git('write-tree').decode().strip()
        self.git('reset', '--hard', 'HEAD')
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.assertEqual(self.scanner('--history', '--all').returncode, 3)

    def test_history_scanner_checks_direct_blob_refs(self):
        (self.repo / 'blob-source').write_text(FAKE)
        oid = self.git('hash-object', '-w', 'blob-source').decode().strip()
        (self.repo / 'blob-source').unlink()
        self.git('update-ref', 'refs/checkpoints/blob', oid)
        self.assertEqual(self.scanner('--history', '--all').returncode, 2)

    def test_tree_symlink_is_reported_as_incomplete(self):
        (self.repo / 'link').symlink_to('readme.txt')
        self.assertEqual(self.scanner().returncode, 3)


if __name__ == '__main__':
    unittest.main()
