import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
GATE = PLUGIN / 'scripts/gate.py'

class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global GATE
        cls.plugin_temp = tempfile.TemporaryDirectory()
        fixture = Path(cls.plugin_temp.name)
        for directory in ('scripts', 'skills', 'agents', 'hooks', 'templates', '.claude-plugin'):
            shutil.copytree(PLUGIN / directory, fixture / directory)
        GATE = fixture / 'scripts/gate.py'

    @classmethod
    def tearDownClass(cls):
        cls.plugin_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / 'repo with space'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo / '.gitignore').write_text('.vibe-shield/\n')
        (self.repo / 'file').write_text('safe\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def gate(self, *args, cwd=None, input=None):
        return subprocess.run(['python3', str(GATE), *args], cwd=cwd or self.repo,
                              text=True, input=input, capture_output=True)

    def approve(self):
        self.assertEqual(self.gate('write', 'begin').returncode, 0)
        result = self.gate('write', 'pass', '0', '0', '0', '0', '--scope', 'full', '--complete')
        self.assertEqual(result.returncode, 0, result.stderr)

    def dispatch(self, command, cwd=None):
        return self.gate('dispatch', input=json.dumps({'cwd': str(cwd or self.repo), 'tool_input': {'command': command}}))

    def test_wrapper_maps_runtime_failure_to_blocking_exit(self):
        bin_dir = Path(self.temp.name) / 'fake-bin'
        bin_dir.mkdir()
        python = bin_dir / 'python3'
        python.write_text('#!/bin/sh\nexit 1\n')
        python.chmod(0o755)
        env = dict(os.environ, PATH=str(bin_dir) + ':' + os.environ['PATH'])
        for wrapper in ('guard-bash.sh', 'guard-push.sh', 'write-status.sh'):
            result = subprocess.run(['/bin/bash', str(GATE.parent / wrapper)], cwd=self.repo,
                                    env=env, text=True, input='{}', capture_output=True)
            self.assertEqual(result.returncode, 2, wrapper)

    def test_valid_gate_can_publish(self):
        self.approve()
        self.assertEqual(self.dispatch('git push').returncode, 0)

    def test_quoted_push_is_checked(self):
        self.assertEqual(self.dispatch('git p\"u\"sh').returncode, 2)

    def test_compound_commit_push_blocked(self):
        self.approve()
        self.assertEqual(self.dispatch('git commit -m x && git push').returncode, 2)

    def test_worktree_index_untracked_and_ref_changes_invalidate(self):
        for mutation in ('worktree', 'index', 'untracked', 'ref'):
            with self.subTest(mutation=mutation):
                self.approve()
                if mutation == 'worktree':
                    (self.repo / 'file').write_text('changed')
                elif mutation == 'index':
                    self.git('add', '.')
                elif mutation == 'untracked':
                    (self.repo / 'new').write_text('new')
                else:
                    self.git('branch', 'other')
                self.assertEqual(self.gate('--check').returncode, 2)

    def test_directory_and_missing_symlinks_block_audit(self):
        target = Path(self.temp.name) / 'external'
        target.mkdir()
        (target / 'file').write_text('safe')
        link = self.repo / 'linked'
        link.symlink_to(target, target_is_directory=True)
        self.git('add', 'linked')
        self.assertEqual(self.gate('write', 'begin').returncode, 2)
        link.unlink()
        link.symlink_to(target / 'missing')
        self.assertEqual(self.gate('write', 'begin').returncode, 2)

    def test_metadata_secrets_in_commit_and_tag_block_publication(self):
        for metadata in ('commit', 'tag'):
            with self.subTest(metadata=metadata):
                if metadata == 'commit':
                    self.git('commit', '--allow-empty', '-m', 'AKIA' + 'Z' * 16)
                else:
                    self.git('reset', '--hard', 'HEAD~1')
                    self.git('tag', '-a', 'metadata-secret', '-m', 'AKIA' + 'Z' * 16)
                self.approve()
                result = self.dispatch('git push --tags origin')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('AKIA' + 'Z' * 16, result.stdout + result.stderr)

    def test_noncommit_tag_blocks_mirror_publication(self):
        result = subprocess.run(['git', '-C', str(self.repo), 'hash-object', '-w', '--stdin'],
                                input='AKIA' + 'Z' * 16, text=True, capture_output=True, check=True)
        self.git('update-ref', 'refs/tags/blob-secret', result.stdout.strip())
        self.approve()
        self.assertEqual(self.dispatch('git push --mirror origin').returncode, 2)
        self.assertEqual(self.dispatch('git push --tags origin').returncode, 2)

    def test_clean_tree_checkpoint_allows_publication(self):
        tree = self.git('rev-parse', 'HEAD^{tree}').stdout.decode().strip()
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.approve()
        self.assertEqual(self.dispatch('git push').returncode, 0)

    def test_checkpoint_submodule_requires_separate_review(self):
        commit = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '160000,' + commit + ',nested')
        tree = self.git('write-tree').stdout.decode().strip()
        self.git('reset', '--hard', 'HEAD')
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.approve()
        result = self.dispatch('git push')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Submodule', result.stderr)

    def test_checkpoint_tree_secret_blocks_publication(self):
        (self.repo / 'file').write_text('AKIA' + 'Z' * 16)
        self.git('add', '.')
        tree = self.git('write-tree').stdout.decode().strip()
        self.git('reset', '--hard', 'HEAD')
        self.git('update-ref', 'refs/codex/turn-diffs/checkpoint', tree)
        self.approve()
        self.assertEqual(self.dispatch('git push').returncode, 2)

    def test_unreferenced_annotated_tag_metadata_blocks(self):
        self.git('tag', '-a', 'temporary', '-m', 'AKIA' + 'Z' * 16)
        oid = self.git('rev-parse', 'temporary').stdout.decode().strip()
        self.git('tag', '-d', 'temporary')
        self.approve()
        self.assertEqual(self.dispatch('git push origin ' + oid + ':refs/tags/release').returncode, 2)

    def test_unexpected_gate_directory_content_invalidates(self):
        self.approve()
        path = self.repo / '.vibe-shield/runtime.js'
        path.write_text('export const value = 1;')
        self.assertEqual(self.gate('--check').returncode, 2)
        self.approve()
        path.write_text('export const value = 2;')
        self.assertEqual(self.gate('--check').returncode, 2)

    def test_malformed_hook_json_blocks(self):
        for payload in ['[]', '{"tool_input": []}', '{"tool_input": {"command": null}}']:
            self.assertEqual(self.gate('dispatch', input=payload).returncode, 2)

    def test_ignored_build_output_change_invalidates(self):
        (self.repo / '.gitignore').write_text('.vibe-shield/\ndist/\n')
        (self.repo / 'dist').mkdir()
        output = self.repo / 'dist/app.js'
        output.write_text('safe')
        self.approve()
        output.write_text('changed artifact')
        self.assertEqual(self.gate('--check').returncode, 2)

    def test_expired_same_head_is_rejected(self):
        self.approve()
        path = self.repo / '.vibe-shield/status.json'
        data = json.loads(path.read_text())
        data['epoch'] -= 1801
        path.write_text(json.dumps(data))
        self.assertEqual(self.gate('--check').returncode, 2)

    def test_begin_snapshot_prevents_approving_changed_inputs(self):
        self.gate('write', 'begin')
        (self.repo / 'file').write_text('changed during audit')
        self.assertEqual(self.gate('write', 'pass', '0', '0', '0', '0', '--scope', 'full', '--complete').returncode, 2)
        self.assertEqual(self.gate('--check').returncode, 2)

    def test_incomplete_or_partial_pass_invalidates_previous_pass(self):
        for args in [('fail', '0', '0', '0', '0'), ('incomplete', '0', '0', '0', '0'), ('pass', '0', '0', '0', '0'), ('pass', '-1', '0', '0', '0')]:
            self.approve()
            self.gate('write', *args)
            self.assertEqual(self.gate('--check').returncode, 2)

    def test_git_c_uses_target_repository(self):
        self.approve()
        target = Path(self.temp.name) / 'second'
        target.mkdir()
        subprocess.run(['git', 'init', '-q', str(target)], check=True)
        self.assertEqual(self.dispatch('git -C "' + str(target) + '" push').returncode, 2)
        self.assertEqual(self.dispatch('git -C "' + str(self.repo) + '" --no-pager push', cwd=target).returncode, 0)

    def test_ambiguous_shell_and_git_options_block(self):
        self.approve()
        for command in ['cd /tmp && git push', 'git -c alias.x=push x', 'env X=1 git push', 'sh -c "git push"', 'git push > /tmp/log', 'git --git-dir=/tmp/x push', 'vercel /tmp/other', 'npm --prefix /tmp publish', 'gh repo create x', 'gh release create x', 'aws s3 sync . s3://bucket']:
            self.assertEqual(self.dispatch(command).returncode, 2, command)

    def test_reuse_invalidates_until_complete_and_preserves_expiry(self):
        self.approve()
        path = self.repo / '.vibe-shield/status.json'
        original = json.loads(path.read_text())['epoch']
        self.assertEqual(self.gate('write', 'begin', '--reuse').returncode, 0)
        self.assertEqual(self.gate('--check').returncode, 2)
        result = self.gate('write', 'pass', '0', '0', '0', '0', '--scope', 'full', '--complete')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(path.read_text())['epoch'], original)

    def test_benign_read_commands_are_not_publication(self):
        for command in ['cat scripts/guard-commit.sh', 'git log --grep=push', 'rg deploy .']:
            self.assertEqual(self.dispatch(command).returncode, 0, command)

    def test_subdirectory_status_written_at_root(self):
        sub = self.repo / 'sub'
        sub.mkdir()
        self.assertEqual(self.gate('write', 'begin', cwd=sub).returncode, 0)
        self.assertTrue((self.repo / '.vibe-shield/status.json').exists())
        self.assertFalse((sub / '.vibe-shield').exists())

    def test_explicit_detached_commit_source_is_scanned(self):
        (self.repo / 'file').write_text('AKIA' + 'Z' * 16)
        self.git('add', '.')
        self.git('commit', '-qm', 'synthetic')
        revision = self.git('rev-parse', 'HEAD').stdout.decode().strip()
        self.git('reset', '--hard', 'HEAD~1')
        self.approve()
        self.assertEqual(self.dispatch('git push origin ' + revision + ':refs/heads/test').returncode, 2)

    def test_history_secret_cannot_be_hidden_by_clean_worktree(self):
        (self.repo / 'file').write_text('AKIA' + 'Z' * 16)
        self.git('add', '.')
        self.git('commit', '-qm', 'synthetic credential')
        (self.repo / 'file').write_text('safe')
        self.git('add', '.')
        self.git('commit', '-qm', 'remove')
        self.approve()
        self.assertEqual(self.dispatch('git push').returncode, 2)

if __name__ == '__main__':
    unittest.main()
