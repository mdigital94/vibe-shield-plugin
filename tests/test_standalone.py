import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from vibe_shield.cli import main
from vibe_shield.contracts import ProviderError, ReviewResult
from vibe_shield.review import collect


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'app.py').write_text('print("hello")\n')

    def review(self, *more):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = main(['review', str(self.root), '--mode', 'api', '--provider', 'openai',
                           '--model', 'user-selected-model', '--file', 'app.py', *more])
        return result, json.loads(out.getvalue())

    def test_preview_does_not_contact_provider_or_mutate_project(self):
        with patch('vibe_shield.providers.run_api') as call:
            code, result = self.review()
        call.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'preview')
        self.assertFalse((self.root / '.vibe-shield').exists())
        self.assertNotIn('content', result['files'][0])

    def test_explicit_model_and_redacted_input_reach_provider_without_pass(self):
        secret = 'sk_live_' + 'A' * 30
        (self.root / 'app.py').write_text('TOKEN = "' + secret + '"\nprint("hello")\n')
        reply = ReviewResult('Nessun problema. ' + secret, 'returned-model', {'input_tokens': 20})
        with patch('vibe_shield.providers.run_api', return_value=reply) as call:
            code, result = self.review('--execute')
        self.assertEqual(code, 0)
        self.assertEqual(call.call_args.args[:2], ('openai', 'user-selected-model'))
        self.assertNotIn(secret, call.call_args.args[2])
        self.assertNotIn(secret, json.dumps(result))
        self.assertFalse(result['gate_authorized'])
        status = json.loads((self.root / '.vibe-shield/status.json').read_text())
        self.assertNotEqual(status['result'], 'pass')

    def test_failed_provider_leaves_gate_incomplete(self):
        with patch('vibe_shield.providers.run_api', side_effect=ProviderError('Modello non disponibile')):
            code, result = self.review('--execute')
        self.assertEqual(code, 3)
        self.assertFalse(result['gate_authorized'])
        self.assertNotEqual(json.loads((self.root / '.vibe-shield/status.json').read_text())['result'], 'pass')

    def test_partial_review_is_redacted_and_never_reported_complete(self):
        secret = 'sk_live_' + 'A' * 30
        reply = ReviewResult('Finding\n' + secret, 'model', {}, complete=False,
                             error='Timeout', response_segments=2)
        with patch('vibe_shield.providers.run_api', return_value=reply):
            code, result = self.review('--execute')
        self.assertEqual(code, 3)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['error'], 'Timeout')
        self.assertNotIn(secret, result['review'])
        self.assertIn('Finding', result['review'])
        self.assertFalse(result['response_complete'])
        self.assertFalse(result['gate_authorized'])

    def test_mutation_during_review_invalidates_result(self):
        def mutate(*a, **kw):
            (self.root / 'app.py').write_text('changed\n')
            return ReviewResult('ok', None, {})
        with patch('vibe_shield.providers.run_api', side_effect=mutate):
            code, result = self.review('--execute')
        self.assertEqual(code, 3)
        self.assertTrue(result['repository_changed'])

    def test_report_keeps_finding_around_inline_sensitive_expression(self):
        text = "RISULTATI\nAlta app.py:3: password nel log: `return 'password=' + password`.\nRimedio: omettere il valore."
        with patch('vibe_shield.providers.run_api', return_value=ReviewResult(text,'model',{})):
            code, result = self.review('--execute')
        self.assertEqual(code,0)
        self.assertIn('Alta app.py:3',result['review'])
        self.assertIn('Rimedio',result['review'])
        self.assertIn('+ password',result['review'])

    def test_fully_redacted_report_is_not_an_available_review(self):
        for text in ('[REDACTED]', '```python\n[REDACTED]\n```', 'RISULTATI\npassword=[REDACTED]'):
            with self.subTest(text=text), patch('vibe_shield.providers.run_api', return_value=ReviewResult(text,'model',{})):
                code, result = self.review('--execute')
            self.assertEqual(code,3)
            self.assertEqual(result['status'],'incomplete')
            self.assertFalse(result['gate_authorized'])

    def test_sensitive_names_symlinks_and_traversal_rejected(self):
        (self.root / '.env').write_text('value')
        (self.root / 'link.py').symlink_to(self.root / 'app.py')
        for name in ('.env', 'link.py', '../outside.py'):
            with self.subTest(name=name), self.assertRaises(ProviderError):
                collect(self.root, [name], 1000)

    def test_binary_and_oversized_input_rejected_without_truncation(self):
        for data in (b'a\0b', b'x' * 1001):
            (self.root / 'app.py').write_bytes(data)
            with self.assertRaises(ProviderError):
                collect(self.root, ['app.py'], 1000)

    def test_environment_key_redacted_even_for_unknown_format(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unusual-private-value'}):
            (self.root / 'app.py').write_text('value = "unusual-private-value"')
            result = collect(self.root, ['app.py'], 1000)
        self.assertNotIn('unusual-private-value', result[0]['content'])

    def test_local_scan_exit_codes_and_check_without_ai(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', 'app.py'], check=True)
        with patch('vibe_shield.providers.run_api') as call:
            self.assertEqual(main(['scan', str(self.root)]), 0)
            self.assertEqual(main(['check', str(self.root)]), 2)
        call.assert_not_called()

    def test_quoted_keys_and_multiline_private_key_are_masked(self):
        (self.root / 'app.py').write_text('{"password": "generic-secret-value"}\n' +
            '-----BEGIN ' + 'PRIVATE KEY-----\nprivate-key-body\n-----END PRIVATE KEY-----')
        result = collect(self.root, ['app.py'], 1000)[0]['content']
        self.assertNotIn('generic-secret-value', result)
        self.assertNotIn('private-key-body', result)

    def test_parent_directory_swap_cannot_read_outside_root(self):
        (self.root / 'd').mkdir()
        (self.root / 'd' / 'app.py').write_text('inside')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'app.py').write_text('outside-private-data')
        real_open = os.open
        def swap(path, flags, *args, **kwargs):
            if path == 'd' and 'dir_fd' in kwargs:
                (self.root / 'd').rename(self.root / 'old-d')
                (self.root / 'd').symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)
        with patch('vibe_shield.review.os.open', side_effect=swap), self.assertRaises(ProviderError):
            collect(self.root, ['d/app.py'], 1000)

    def test_dry_run_rejects_endpoint_credentials_without_printing_them(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['review', str(self.root), '--mode', 'api', '--provider', 'ollama',
                         '--model', 'chosen', '--file', 'app.py', '--endpoint',
                         'https://user:private-password@example.com'])
        self.assertEqual(code, 3)
        self.assertNotIn('private-password', output.getvalue())
