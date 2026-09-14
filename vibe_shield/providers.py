"""Bounded, non-agentic HTTP adapters; usage retains each provider's semantics.

OpenAI/Gemini input includes cached tokens; Anthropic input excludes cache
reads/writes. Cache fields must never be blindly added to input. Missing is None.
Endpoints for custom services are base URLs (compatible usually ends in /v1).
"""
import http.client
import ipaddress
import json
import math
import os
from urllib import error, parse, request

from .contracts import ProviderError, ReviewResult

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
PROVIDERS = ('openai', 'anthropic', 'gemini', 'ollama', 'openai-compatible')


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('API redirects are not permitted.')


def _base_url(value):
    if not isinstance(value, str) or not value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise ProviderError('Invalid API endpoint.')
    try:
        url = parse.urlsplit(value)
        host = url.hostname
        port = url.port
        if not host or url.username is not None or url.password is not None or url.query or url.fragment or '?' in value or '#' in value or '\\' in value:
            raise ValueError()
        local = host == 'localhost'
        try:
            local = local or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if url.scheme != 'https' and not (url.scheme == 'http' and local):
            raise ValueError()
        if port is not None and port == 0:
            raise ValueError()
        return value.rstrip('/')
    except (ValueError, UnicodeError):
        raise ProviderError('Endpoint requires HTTPS, or HTTP on loopback, without credentials, query or fragment.') from None


def _post(url, headers, payload, timeout):
    try:
        req = request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        # Explicitly disable proxy inheritance: a local endpoint must stay local.
        opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
        with opener.open(req, timeout=timeout) as response:
            if response.status != 200:
                raise ProviderError('API returned an unsuccessful HTTP status.')
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProviderError('API response exceeds the size limit.')
        result = json.loads(raw.decode('utf-8'))
        if not isinstance(result, dict):
            raise ProviderError('Malformed API response.')
        return result
    except ProviderError:
        raise
    except error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ProviderError('API request failed (HTTP %d).' % code) from None
    except (OSError, ValueError, UnicodeError, error.URLError, http.client.HTTPException):
        raise ProviderError('API transport or JSON response failed.') from None


def _count(data, key):
    value = data.get(key)
    if value is not None and (type(value) is not int or value < 0):
        raise ProviderError('Malformed API usage metadata.')
    return value


def _dict(value):
    if not isinstance(value, dict):
        raise ProviderError('Malformed API response.')
    return value


def _optional_dict(value):
    return {} if value is None else _dict(value)


def _usage(data, inp, out, read=None, write=None):
    data = _dict(data)
    return {'input_tokens': _count(data, inp), 'output_tokens': _count(data, out),
            'cache_read_tokens': _count(data, read) if read else None,
            'cache_write_tokens': _count(data, write) if write else None}


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ProviderError('API did not return a complete text review.')
    return value


def _parse(provider, data):
    if data.get('error'):
        raise ProviderError('API returned an error.')
    model = data.get('modelVersion' if provider == 'gemini' else 'model')
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise ProviderError('Malformed API model metadata.')
    if provider in ('openai', 'openai-compatible'):
        choices = data['choices']
        if not isinstance(choices, list) or len(choices) != 1 or _dict(choices[0]).get('finish_reason') != 'stop':
            raise ProviderError('API review was incomplete or requested tools.')
        message = _dict(choices[0]['message'])
        if message.get('tool_calls') or message.get('function_call') or message.get('refusal') or message.get('role') != 'assistant':
            raise ProviderError('API review was refused or requested tools.')
        text = _text(message.get('content'))
        raw_usage = _optional_dict(data.get('usage'))
        usage = _usage(raw_usage, 'prompt_tokens', 'completion_tokens')
        usage['cache_read_tokens'] = _count(_optional_dict(raw_usage.get('prompt_tokens_details')), 'cached_tokens')
    elif provider == 'anthropic':
        if data.get('stop_reason') != 'end_turn' or data.get('role') != 'assistant':
            raise ProviderError('API review was incomplete or requested tools.')
        blocks = data['content']
        if not isinstance(blocks, list) or not blocks:
            raise ProviderError('Malformed API response.')
        parts = []
        for block in blocks:
            block = _dict(block)
            if block.get('type') != 'text':
                raise ProviderError('API returned unsupported non-text content.')
            parts.append(_text(block.get('text')))
        text = '\n'.join(parts)
        usage = _usage(_optional_dict(data.get('usage')), 'input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
    elif provider == 'gemini':
        candidates = data['candidates']
        if not isinstance(candidates, list) or len(candidates) != 1 or _dict(candidates[0]).get('finishReason') != 'STOP':
            raise ProviderError('API review was incomplete or blocked.')
        parts = _dict(candidates[0]['content'])['parts']
        if not isinstance(parts, list) or not parts:
            raise ProviderError('Malformed API response.')
        texts = []
        for part in parts:
            part = _dict(part)
            if set(part) - {'text', 'thought', 'thoughtSignature'} or 'text' not in part:
                raise ProviderError('API returned unsupported non-text content.')
            if not part.get('thought'):
                texts.append(_text(part['text']))
        text = _text('\n'.join(texts))
        usage = _usage(_optional_dict(data.get('usageMetadata')), 'promptTokenCount', 'candidatesTokenCount', 'cachedContentTokenCount')
    else:
        if data.get('done') is not True or data.get('done_reason') != 'stop':
            raise ProviderError('API review was incomplete.')
        message = _dict(data['message'])
        if message.get('tool_calls') or message.get('role') != 'assistant':
            raise ProviderError('API requested tools or returned malformed content.')
        text = _text(message.get('content'))
        usage = _usage(data, 'prompt_eval_count', 'eval_count')
    return ReviewResult(text=text, model=model, usage=usage)


def run_api(provider, model, prompt, *, endpoint=None, timeout=60, max_output_tokens=2000):
    """One explicit model request; no retries, tools, fallback, or gate changes."""
    if provider not in PROVIDERS:
        raise ProviderError('Unsupported API provider.')
    if not isinstance(model, str) or not model.strip() or any(ord(c) < 32 for c in model):
        raise ProviderError('An explicit model is required.')
    if not isinstance(prompt, str) or not prompt.strip():
        raise ProviderError('A nonempty review prompt is required.')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ProviderError('Timeout must be finite and between 0 and 600 seconds.')
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 1000000:
        raise ProviderError('Invalid output token limit.')
    if endpoint is not None and provider not in ('ollama', 'openai-compatible'):
        raise ProviderError('Named cloud providers use their fixed API endpoint.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False}
    key_name = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY', 'openai-compatible': 'VIBE_SHIELD_API_KEY'}.get(provider)
    key = os.environ.get(key_name, '') if key_name else ''
    if key_name and not key.strip():
        raise ProviderError('Missing API credential in environment variable ' + key_name + '.')
    if any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise ProviderError('Invalid API credential format.')
    if provider == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
        headers['Authorization'] = 'Bearer ' + key
        payload['max_completion_tokens'] = max_output_tokens
    elif provider == 'anthropic':
        url = 'https://api.anthropic.com/v1/messages'
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
        payload['max_tokens'] = max_output_tokens
    elif provider == 'gemini':
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + parse.quote(model, safe='') + ':generateContent'
        headers['x-goog-api-key'] = key
        payload = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': max_output_tokens}}
    elif provider == 'ollama':
        url = _base_url(endpoint if endpoint is not None else 'http://127.0.0.1:11434') + '/api/chat'
        payload['options'] = {'num_predict': max_output_tokens}
    else:
        url = _base_url(endpoint) + '/chat/completions'
        headers['Authorization'] = 'Bearer ' + key
        payload['max_tokens'] = max_output_tokens
    data = _post(url, headers, payload, timeout)
    try:
        return _parse(provider, data)
    except (KeyError, TypeError, IndexError, AttributeError):
        raise ProviderError('Malformed API response.') from None
