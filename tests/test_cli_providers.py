import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibe_shield.cli_providers import run_cli
from vibe_shield.contracts import ProviderError


@unittest.skipUnless(os.name == "posix", "POSIX process isolation")
class CliProviderTests(unittest.TestCase):
    def fake(self, body):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        executable = Path(directory.name) / "claude"
        executable.write_text("#!" + sys.executable + "\n" + body)
        executable.chmod(0o700)
        mocked = patch("vibe_shield.cli_providers.shutil.which", return_value=str(executable))
        mocked.start()
        self.addCleanup(mocked.stop)
        return directory.name

    def test_explicit_model_stdin_isolation_and_usage(self):
        self.fake('''import os, sys, json
args = sys.argv[1:]
assert args[args.index('--model') + 1] == 'chosen-model'
assert args[args.index('--tools') + 1] == ''
assert args[args.index('--setting-sources') + 1] == ''
assert '--safe-mode' in args and '--strict-mcp-config' in args
assert args[args.index('--output-format')+1] == 'stream-json' and '--verbose' in args
assert '--disable-slash-commands' in args and '--no-session-persistence' in args
assert json.loads(args[args.index('--mcp-config') + 1]) == {'mcpServers': {}}
assert json.loads(args[args.index('--settings') + 1])['disableAllHooks'] is True
assert 'NODE_OPTIONS' not in os.environ
assert os.environ['USER'] == 'fixture-user'
assert os.environ['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] == '55'
assert os.path.basename(os.getcwd()).startswith('vibe-shield-review-')
assert sys.stdin.read() == 'code $(touch BAD)'
print(json.dumps({'type':'assistant','uuid':'a','message':{'id':'m','content':[{'type':'text','text':'review'}]}}))
print(json.dumps({'type':'result','is_error':False,'stop_reason':'end_turn','subtype':'success','result':'review','modelUsage':{'resolved-model':{}}, 'usage':{'input_tokens':12,'output_tokens':8,'cache_read_input_tokens':0}}))
''')
        with patch.dict(os.environ, {"NODE_OPTIONS": "untrusted-loader", "USER": "fixture-user"}):
            result = run_cli("claude", "chosen-model", "code $(touch BAD)", max_output_tokens=55)
        self.assertEqual(result.text, "review")
        self.assertEqual(result.model, "resolved-model")
        self.assertEqual(result.usage, {"input_tokens":12,"output_tokens":8,"cache_read_tokens":0,"cache_write_tokens":None})

    def test_failure_never_exposes_raw_output(self):
        self.fake("import sys\nprint('SECRET output')\nprint('SECRET stderr', file=sys.stderr)\nsys.exit(1)\n")
        with self.assertRaises(ProviderError) as error:
            run_cli("claude", "model", "prompt")
        self.assertNotIn("SECRET", str(error.exception))

    def test_turn_limit_failure_reports_only_known_reason(self):
        self.fake("import json,sys\nprint(json.dumps({'type':'result','subtype':'error_max_turns','result':'SECRET'}))\nsys.exit(1)\n")
        with self.assertRaises(ProviderError) as error:
            run_cli('claude', 'model', 'prompt')
        self.assertIn('limite di turni', str(error.exception))
        self.assertNotIn('SECRET', str(error.exception))

    def test_malformed_and_incomplete_results_rejected(self):
        for payload in ("not json", '[]', '{"subtype":"error_max_turns","result":"partial"}', '{"subtype":"success","result":""}'):
            with self.subTest(payload=payload):
                with patch("vibe_shield.cli_providers.shutil.which", return_value="fake"), patch("vibe_shield.cli_providers._execute", return_value=payload.encode()):
                    with self.assertRaises(ProviderError):
                        run_cli("claude", "model", "prompt")

    def test_timeout_and_descendant_cleanup(self):
        directory = self.fake("import os,time\nif os.fork() == 0:\n time.sleep(0.5)\n open(__file__ + '.escaped','w').write('bad')\ntime.sleep(5)\n")
        with self.assertRaisesRegex(ProviderError, "Timeout"):
            run_cli("claude", "model", "prompt", timeout=0.1)
        import time
        time.sleep(0.6)
        self.assertFalse((Path(directory) / "claude.escaped").exists())

    def test_both_output_streams_are_bounded(self):
        for stream in ("stdout", "stderr"):
            with self.subTest(stream=stream):
                self.fake("import sys\nsys." + stream + ".write('x' * 2000000)\n")
                with self.assertRaisesRegex(ProviderError, "limite"):
                    run_cli("claude", "model", "prompt")

    def test_timeout_preserves_completed_segment_without_success(self):
        self.fake("import json,time\nprint(json.dumps({'type':'assistant','uuid':'a','message':{'content':[{'type':'text','text':'prefix'}]}}),flush=True)\ntime.sleep(5)\n")
        result = run_cli('claude', 'model', 'prompt', timeout=2)
        self.assertEqual(result.text, 'prefix')
        self.assertFalse(result.complete)
        self.assertIn('Timeout', result.error)

    def test_unknown_usage_not_zero(self):
        raw = ('\n'.join(json.dumps(e) for e in [
            {"type":"assistant","uuid":"a","message":{"content":[{"type":"text","text":"review"}]}},
            {"type":"result","subtype":"success","is_error":False,"stop_reason":"end_turn","usage":{"input_tokens":True,"output_tokens":-1}}
        ])).encode()
        with patch("vibe_shield.cli_providers.shutil.which", return_value="fake"), patch("vibe_shield.cli_providers._execute", return_value=raw):
            result = run_cli("claude", "model", "prompt")
        self.assertIsNone(result.model)
        self.assertTrue(all(value is None for value in result.usage.values()))

    def test_invalid_configuration_fails_before_execution(self):
        with patch("vibe_shield.cli_providers.subprocess.Popen") as process:
            for provider, model, kwargs in (("codex", "model", {}), ("gemini", "model", {}), ("claude", "", {}), ("claude", "--bad", {}), ("claude", "m", {"timeout":float('nan')}), ("claude", "m", {"max_output_tokens":False})):
                with self.subTest(provider=provider, model=model, kwargs=kwargs):
                    with self.assertRaises(ProviderError):
                        run_cli(provider, model, "prompt", **kwargs)
            process.assert_not_called()

    def test_missing_binary_has_actionable_error(self):
        with patch("vibe_shield.cli_providers.shutil.which", return_value=None):
            with self.assertRaisesRegex(ProviderError, "installato"):
                run_cli("claude", "model", "prompt")
