"""Synthetic privacy checks and retained evidence; no model/network calls."""
import ast
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from vibe_shield.review import redact


class RedactionTests(unittest.TestCase):
    def test_benchmark_logging_expressions_keep_password_reference_and_line(self):
        cases = json.loads((Path(__file__).resolve().parents[1] / 'benchmarks/cases_extra.json').read_text())
        for case in cases:
            if case['id'] not in ('c21', 'c29'):
                continue
            with self.subTest(case=case['id']):
                source = case['files']['app.py']
                result = redact(source)
                evidence = result.splitlines()[case['expected'][0]['line_start'] - 1]
                self.assertIn('return ', evidence)
                self.assertIn('password=', evidence)
                self.assertIn('+ password', evidence)
                ast.parse(result)

    def test_literal_concatenated_password_is_masked_but_reference_is_visible(self):
        result = redact('return "password=" + supplied + "private-value"')
        self.assertIn('+ supplied', result)
        self.assertNotIn('private-value', result)
        ast.parse(result)

    def test_fstring_interpolation_keeps_reference_and_masks_literal_expression(self):
        source = '''return f"password={password} token={'private-value'}"'''
        result = redact(source)
        self.assertIn('{password}', result)
        self.assertNotIn('private-value', result)
        ast.parse(result)

    def test_literal_values_are_masked_without_removing_assignments(self):
        for source, secret in [('password = "private-value"', 'private-value'),
                               ('password = "password="', 'password='),
                               ('password = 983764', '983764'),
                               ('password = "password=private-value"', 'private-value'),
                               ('password = "pri" "vate-value"', 'vate-value')]:
            with self.subTest(source=source):
                result = redact(source)
                self.assertIn('password = ', result)
                self.assertNotIn(secret, result)

    def test_json_keys_and_structure_remain_while_values_are_masked(self):
        result = redact('{"password": "private-value", "port": 1234}')
        self.assertIn('"password":', result)
        self.assertNotIn('private-value', result)
        ast.parse(result)

    def test_dictionary_keys_cannot_carry_literal_credentials_through_redaction(self):
        for source in ('record = {"password=SYNTHETIC_NOT_A_REAL_CREDENTIAL": 1}',
                       'password = {"SYNTHETIC_NOT_A_REAL_CREDENTIAL": True}',
                       'record = {"password": {"SYNTHETIC_NOT_A_REAL_CREDENTIAL": True}}'):
            with self.subTest(source=source):
                self.assertNotIn('SYNTHETIC_NOT_A_REAL_CREDENTIAL', redact(source))

    def test_comments_on_same_line_do_not_hide_assignment_from_redactor(self):
        result = redact('password = "private-value" # token=comment-value')
        self.assertNotIn('private-value', result)
        self.assertNotIn('comment-value', result)

    def test_multiline_string_is_fully_masked_and_line_numbers_remain(self):
        source = 'password = """first-private\nsecond-private\nlast-private"""\nprint(password)'
        result = redact(source)
        for value in ('first-private', 'second-private', 'last-private'):
            self.assertNotIn(value, result)
        self.assertEqual(result.splitlines()[3], 'print(password)')

    def test_unicode_ast_columns_do_not_corrupt_or_leak_values(self):
        result = redact('label = "caffè"; password = "private-value"')
        self.assertNotIn('private-value', result)
        self.assertIn('label = "caffè"', result)
        ast.parse(result)

    def test_ambiguous_bare_sensitive_defaults_and_bindings_are_masked(self):
        for source in ('def f(password=SYNTHETIC_VALUE): pass',
                       'def f(*, password=SYNTHETIC_VALUE): pass',
                       '(password := SYNTHETIC_VALUE)',
                       'obj.password = SYNTHETIC_VALUE'):
            with self.subTest(source=source):
                self.assertNotIn('SYNTHETIC_VALUE', redact(source))

    def test_unquoted_env_and_yaml_values_fail_closed(self):
        for source in ('PASSWORD=private_value', 'PASSWORD=private-value',
                       'password: private_value', '{"password": private_value}',
                       'password: @private-value'):
            with self.subTest(source=source):
                self.assertNotIn('private', redact(source))

    def test_unsupported_multiline_secret_formats_fail_closed(self):
        for source in ('password: |\n  private-value\n',
                       'password: |-\n  private-value\n',
                       'password = """\nprivate-value',
                       'password = {\n"value": "private-value"',
                       'password: "first\nprivate-value\nlast"',
                       'password=<<EOF\nprivate-value\nEOF'):
            with self.subTest(source=source):
                self.assertNotIn('private-value', redact(source))

    def test_known_tokens_and_environment_values_are_still_private(self):
        token = 'sk_live_' + 'A' * 30
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unknown-private-value'}):
            result = redact('print("' + token + '")\nprint("unknown-private-value")')
        self.assertNotIn(token, result)
        self.assertNotIn('unknown-private-value', result)

    def test_pem_body_is_masked_without_shifting_following_line(self):
        source = '-----BEGIN ' + 'PRIVATE KEY-----\nprivate-body\n-----END PRIVATE KEY-----\nprint(1)'
        result = redact(source)
        self.assertNotIn('private-body', result)
        self.assertEqual(result.splitlines()[3], 'print(1)')

    def test_unaffected_code_is_preserved(self):
        source = 'def check(password):\n    return verify(password)'
        self.assertEqual(redact(source), source)


class OutputRedactionTests(unittest.TestCase):
    def redact(self, text):
        from vibe_shield.review import redact_output
        return redact_output(text)

    def test_concise_finding_retains_identity_inline_evidence_and_remedy(self):
        source = ('RISULTATI\n\n- ALTA app.py:2 — CWE-532: la password è scritta nel log; '
                  'prova: `return "password=" + password`. Rimedio: rimuovere la password.\n\n'
                  'LIMITI\nSolo i file selezionati.')
        self.assertEqual(self.redact(source), source)

    def test_detailed_report_survives_ambiguous_code_block(self):
        source = ('## ALTA — CWE-532, app.py:3\n\nLa password finisce nel log.\n\n'
                  '```python\npassword = """\nSYNTHETIC_PRIVATE_VALUE\n```\n\n'
                  'Rimedio: eliminare le credenziali dai log.\n\nLIMITI\nSolo questo file.')
        result = self.redact(source)
        self.assertIn('## ALTA — CWE-532, app.py:3', result)
        self.assertIn('Rimedio: eliminare', result)
        self.assertIn('LIMITI\nSolo questo file.', result)
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)

    def test_actual_prose_values_are_masked_without_erasing_finding_prefix(self):
        for value in ('SYNTHETIC_PRIVATE_VALUE', '"SYNTHETIC PRIVATE VALUE"',
                      '`SYNTHETIC_PRIVATE_VALUE`', '"first `SYNTHETIC_PRIVATE_VALUE` last"'):
            source = 'ALTA app.py:2 — credential password=' + value + '\n\nRimedio: ruotarla.'
            with self.subTest(value=value):
                result = self.redact(source)
                self.assertIn('ALTA app.py:2', result)
                self.assertIn('Rimedio: ruotarla.', result)
                self.assertNotIn('SYNTHETIC', result)

    def test_quoted_value_keeps_following_remedy(self):
        result = self.redact('ALTA password="private value"; rimedio: rimuovere il valore.')
        self.assertNotIn('private value', result)
        self.assertIn('; rimedio: rimuovere il valore.', result)

    def test_multiline_prose_value_masks_relevant_block_only(self):
        result = self.redact('ALTA app.py:2 password: |\n  SYNTHETIC_PRIVATE_VALUE\n\nLIMITI\nScope ristretto.')
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
        self.assertIn('ALTA app.py:2', result)
        self.assertIn('LIMITI\nScope ristretto.', result)

    def test_fences_used_as_prose_secret_values_and_metadata_are_private(self):
        for source in ('ALTA password:\n```text\nSYNTHETIC_PRIVATE_VALUE\n```\n\nRimedio.',
                       'ALTA\n```python password=SYNTHETIC_PRIVATE_VALUE\nprint(1)\n```\n\nRimedio.'):
            with self.subTest(source=source):
                result = self.redact(source)
                self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
                self.assertIn('ALTA', result)
                self.assertIn('Rimedio.', result)

    def test_known_token_does_not_erase_its_finding_or_leave_a_suffix(self):
        token = 'sk_live_' + 'A' * 45
        source = 'ALTA app.py:2 — credenziale ' + token + '; rimedio: ruotarla.'
        result = self.redact(source)
        self.assertNotIn('A' * 5, result)
        self.assertIn('ALTA app.py:2', result)
        self.assertIn('rimedio: ruotarla.', result)

    def test_pem_and_environment_values_remain_private_in_output(self):
        source = ('ALTA\n-----BEGIN ' + 'PRIVATE KEY-----\nSYNTHETIC_PRIVATE_VALUE\n'
                  '-----END PRIVATE KEY-----\nRimedio: revocare.\nprivate-environment-value')
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'private-environment-value'}):
            result = self.redact(source)
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
        self.assertNotIn('private-environment-value', result)
        self.assertIn('ALTA', result)
        self.assertIn('Rimedio: revocare.', result)

    def test_inline_json_code_and_fstring_keep_structure_and_remove_literals(self):
        result = self.redact('ALTA: `{"password": "SYNTHETIC_PRIVATE_VALUE"}`. '
                             'Prova: `return f"password={password}"`. Rimedio: evitare il log.')
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
        self.assertIn('{password}', result)
        self.assertIn('Rimedio: evitare il log.', result)

    def test_known_match_spanning_spaces_is_not_hidden_by_another_token(self):
        token = 'sk_live_' + 'A' * 30
        source = 'SUPABASE_SERVICE_ROLE = ' + 'eyJ_SYNTHETIC_PRIVATE_VALUE ' + token
        result = self.redact(source)
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
        self.assertNotIn(token, result)

    def test_multiline_values_after_blank_lines_and_crlf_are_not_exposed(self):
        for newline in ('\n', '\r\n'):
            for label in ('password:', 'password: |'):
                for blanks in (1, 2, 3):
                    source = ('ALTA ' + label + newline * blanks +
                              '  SYNTHETIC_PRIVATE_VALUE' + newline * 2 + 'Rimedio: revocare.')
                    with self.subTest(newline=repr(newline), label=label, blanks=blanks):
                        result = self.redact(source)
                        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
                        self.assertIn('ALTA', result)
                        self.assertIn('Rimedio: revocare.', result)

    def test_empty_quoted_password_labels_keep_the_whole_finding(self):
        for quote in ('"', "'"):
            source = ('ALTA app.py:3: la stringa ' + quote + 'password=' + quote +
                      ' viene concatenata con password. Rimedio: rimuovere il segreto.')
            with self.subTest(quote=quote):
                self.assertEqual(self.redact(source), source)

    def test_quoted_assignment_masks_only_enclosed_value_and_retains_suffix(self):
        for quote in ('"', "'"):
            source = ('ALTA app.py:3: ' + quote + 'password=SYNTHETIC_PRIVATE_VALUE' + quote +
                      '. Rimedio: rimuovere il segreto.')
            with self.subTest(quote=quote):
                result = self.redact(source)
                self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
                self.assertIn(quote + 'password=[REDACTED]' + quote, result)
                self.assertIn('. Rimedio: rimuovere il segreto.', result)

    def test_quoted_mapping_keys_still_mask_their_actual_values_in_prose(self):
        for quote in ('"', "'"):
            source = ('ALTA ' + quote + 'password' + quote + ': ' + quote +
                      'SYNTHETIC_PRIVATE_VALUE' + quote + '. Rimedio: revocare.')
            with self.subTest(quote=quote):
                result = self.redact(source)
                self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result)
                self.assertIn('. Rimedio: revocare.', result)
