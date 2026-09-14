"""Assemble completed Claude stream messages; never treat terminal text as a transcript."""
import json
from .contracts import ProviderError, ReviewResult


def count(value):
    return value if type(value) is int and value >= 0 else None


def parse_stream(raw, process_error=None):
    active = {}
    seen = {}
    retired = set()
    aborted = set()
    terminal = None
    error = process_error
    labels = {'error_max_turns': 'limite di turni raggiunto',
              'error_max_budget_usd': 'limite di budget raggiunto',
              'error_during_execution': 'errore durante esecuzione'}
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError
            # Child-agent output is not the main review, including child results.
            if event.get('parent_tool_use_id') is not None:
                continue
            kind = event.get('type')
            if terminal is not None and kind != 'system':
                raise ValueError
            if kind == 'assistant':
                if event.get('is_meta') is True or event.get('is_virtual') is True:
                    continue
                uid = event.get('uuid')
                message = event.get('message')
                supersedes = event.get('supersedes', [])
                if (not isinstance(uid, str) or not uid or not isinstance(message, dict)
                        or not isinstance(message.get('content'), list)
                        or not isinstance(supersedes, list)
                        or any(not isinstance(v, str) for v in supersedes)):
                    raise ValueError
                signature = (message, supersedes, event.get('aborted', False))
                if uid in seen:
                    if seen[uid] != signature:
                        raise ValueError
                    continue
                seen[uid] = signature
                for victim in supersedes:
                    retired.add(victim)
                    active.pop(victim, None)
                if uid in retired:
                    continue
                chunks = []
                for block in message['content']:
                    if not isinstance(block, dict):
                        raise ValueError
                    if block.get('type') == 'text':
                        if not isinstance(block.get('text'), str):
                            raise ValueError
                        chunks.append(block['text'])
                    elif block.get('type') not in ('thinking', 'redacted_thinking'):
                        raise ValueError
                active[uid] = ''.join(chunks)
                if event.get('aborted') is True:
                    aborted.add(uid)
            elif kind == 'tombstone':
                message = event.get('message')
                if not isinstance(message, dict) or not isinstance(message.get('uuid'), str):
                    raise ValueError
                victim = message['uuid']
                retired.add(victim)
                active.pop(victim, None)
            elif kind == 'system':
                if event.get('subtype') == 'model_refusal_fallback':
                    victims = event.get('retracted_message_uuids')
                    if not isinstance(victims, list) or any(not isinstance(v, str) for v in victims):
                        raise ValueError
                    for victim in victims:
                        retired.add(victim)
                        active.pop(victim, None)
            elif kind == 'result':
                terminal = event
            elif kind not in ('user', 'rate_limit_event', 'tool_progress', 'tool_use_summary', 'auth_status'):
                raise ValueError
    except (ValueError, UnicodeError, TypeError):
        error = error or 'Flusso CLI non valido o interrotto; conservati solo i segmenti verificabili.'
    text = ''.join(active.values())
    if aborted.intersection(active):
        error = error or 'Revisione CLI incompleta: messaggio interrotto.'
    if terminal is None:
        error = error or 'Revisione CLI incompleta: risultato conclusivo assente.'
    elif terminal.get('is_error') is not False or terminal.get('subtype') != 'success':
        subtype = terminal.get('subtype')
        label = labels.get(subtype) if isinstance(subtype, str) else None
        error = 'Revisione CLI incompleta: ' + (label or 'errore del provider') + '.'
    elif terminal.get('stop_reason') not in ('end_turn', 'stop_sequence'):
        error = error or 'Revisione CLI incompleta: conclusione del modello non verificata.'
    if not text.strip():
        raise ProviderError(error or 'Il CLI non ha restituito segmenti di revisione testuale.')
    usage = terminal.get('usage', {}) if terminal else {}
    if not isinstance(usage, dict):
        usage = {}
    models = terminal.get('modelUsage') if terminal else None
    model = next(iter(models)) if isinstance(models, dict) and len(models) == 1 else None
    return ReviewResult(text=text, model=model, usage={
        'input_tokens': count(usage.get('input_tokens')),
        'output_tokens': count(usage.get('output_tokens')),
        'cache_read_tokens': count(usage.get('cache_read_input_tokens')),
        'cache_write_tokens': count(usage.get('cache_creation_input_tokens')),
    }, complete=error is None, error=error,
        response_segments=sum(bool(value) for value in active.values()))
