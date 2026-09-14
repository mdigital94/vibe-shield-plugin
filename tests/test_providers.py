import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from vibe_shield.contracts import ProviderError
from vibe_shield import providers as api


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {key: 'fixture-key' for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'VIBE_SHIELD_API_KEY')}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, provider, response, **kwargs):
        with patch.object(api, '_post', return_value=response) as post:
            result = api.run_api(provider, 'chosen-model', 'review', **kwargs)
            return result, post.call_args.args

    def chat(self):
        return {'model': 'chosen-model-version', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Review'}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'prompt_tokens_details': {'cached_tokens': 60}}}

    def test_openai_model_budget_and_cache_are_preserved(self):
        result, (url, headers, payload, timeout) = self.call('openai', self.chat())
        self.assertEqual(payload['model'], 'chosen-model')
        self.assertEqual(payload['max_completion_tokens'], 2000)
        self.assertEqual(result.usage['input_tokens'], 100)
        self.assertEqual(result.usage['cache_read_tokens'], 60)
        self.assertEqual(result.model, 'chosen-model-version')
        self.assertEqual(url, 'https://api.openai.com/v1/chat/completions')

    def test_compatible_requires_explicit_endpoint(self):
        with self.assertRaises(ProviderError):
            api.run_api('openai-compatible', 'model', 'review')
        result, args = self.call('openai-compatible', self.chat(), endpoint='http://127.0.0.1:9000/v1')
        self.assertEqual(args[0], 'http://127.0.0.1:9000/v1/chat/completions')
        self.assertIn('max_tokens', args[2])

    def test_anthropic_cache_is_separate(self):
        result, args = self.call('anthropic', {'role': 'assistant', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'Review'}], 'usage': {'input_tokens': 10, 'output_tokens': 8, 'cache_read_input_tokens': 50, 'cache_creation_input_tokens': 20}})
        self.assertEqual(result.usage, {'input_tokens': 10, 'output_tokens': 8, 'cache_read_tokens': 50, 'cache_write_tokens': 20})
        self.assertIsNone(result.model)
        self.assertEqual(args[1]['anthropic-version'], '2023-06-01')

    def test_gemini_text_and_usage(self):
        result, args = self.call('gemini', {'modelVersion': 'gemini-version', 'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Review'}]}}], 'usageMetadata': {'promptTokenCount': 20, 'candidatesTokenCount': 7, 'cachedContentTokenCount': 10}})
        self.assertEqual(result.text, 'Review')
        self.assertEqual(result.usage['cache_read_tokens'], 10)
        self.assertNotIn('key=', args[0])
        self.assertEqual(args[1]['x-goog-api-key'], 'fixture-key')

    def test_ollama_does_not_need_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result, args = self.call('ollama', {'done': True, 'done_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Review'}, 'prompt_eval_count': 30, 'eval_count': 9})
        self.assertEqual(args[0], 'http://127.0.0.1:11434/api/chat')
        self.assertEqual(args[2]['options'], {'num_predict': 2000})
        self.assertEqual(result.usage['input_tokens'], 30)

    def test_missing_usage_remains_unknown(self):
        response = self.chat()
        del response['usage']
        result, _ = self.call('openai', response)
        self.assertTrue(all(value is None for value in result.usage.values()))

    def test_rejects_incomplete_tools_and_malformed_responses(self):
        responses = [None, {}, {'choices': []}, {'choices': [{'finish_reason': 'length'}]}]
        for key in ('tool_calls', 'function_call', 'refusal'):
            response = self.chat()
            response['choices'][0]['message'][key] = 'present'
            responses.append(response)
        response = self.chat()
        response['usage']['prompt_tokens'] = True
        responses.append(response)
        for response in responses:
            with self.subTest(response=response), self.assertRaises(ProviderError):
                self.call('openai', response)
        for provider, response in [('anthropic', {'stop_reason': 'max_tokens'}), ('gemini', {'candidates': [{'finishReason': 'MAX_TOKENS'}]}), ('ollama', {'done': True, 'done_reason': 'length'})]:
            with self.subTest(provider=provider), self.assertRaises(ProviderError):
                self.call(provider, response)

    def test_url_validation_before_network(self):
        for endpoint in ('http://example.com', 'https://user:secret@example.com', 'https://host?key=secret', 'https://host#secret', 'file:///tmp/a', 'http://127.0.0.1.evil', 'https://host\n', 'https://host:bad', 'https://host\\evil', ''):
            with self.subTest(endpoint=endpoint), patch.object(api, '_post') as post, self.assertRaises(ProviderError):
                api.run_api('openai-compatible', 'model', 'review', endpoint=endpoint)
            post.assert_not_called()
        self.assertEqual(api._base_url('http://[::1]:11434'), 'http://[::1]:11434')

    def test_missing_key_and_fixed_cloud_endpoint(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ProviderError, 'OPENAI_API_KEY'):
            api.run_api('openai', 'model', 'review')
        with self.assertRaises(ProviderError):
            api.run_api('openai', 'model', 'review', endpoint='https://evil')

    def test_invalid_timeout_and_selection(self):
        for timeout in (0, -1, float('inf'), float('nan'), True, 601):
            with self.subTest(timeout=timeout), self.assertRaises(ProviderError):
                api.run_api('ollama', 'model', 'review', timeout=timeout)
        with self.assertRaises(ProviderError):
            api.run_api('ollama', '', 'review')

    def test_redirect_is_never_followed(self):
        with self.assertRaises(ProviderError):
            api._NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://evil')

    def test_http_error_body_and_url_are_not_exposed(self):
        exc = HTTPError('https://host/private', 401, 'fixture-key', {}, io.BytesIO(b'fixture-key'))
        with patch.object(api.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = exc
            with self.assertRaises(ProviderError) as caught:
                api._post('https://host', {}, {}, 10)
        self.assertEqual(str(caught.exception), 'API request failed (HTTP 401).')
        opener.return_value.open.assert_called_once()

    def test_transport_size_limit_and_bad_json(self):
        for body in (b'not-json fixture-key', b'[]', b'x' * (api.MAX_RESPONSE_BYTES + 1)):
            with patch.object(api.request, 'build_opener') as opener:
                response = opener.return_value.open.return_value.__enter__.return_value
                response.status = 200
                response.read.return_value = body
                with self.assertRaises(ProviderError) as caught:
                    api._post('https://host', {}, {}, 10)
                self.assertNotIn('fixture-key', str(caught.exception))
                response.read.assert_called_once_with(api.MAX_RESPONSE_BYTES + 1)


if __name__ == '__main__':
    unittest.main()
