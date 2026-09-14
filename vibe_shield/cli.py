"""Independent command line: local checks and explicitly requested AI reviews."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from . import __version__
from .contracts import ProviderError
from .resources import resource_root
from .review import ASSIGNMENT, collect, prompt_for, redact, redact_output

API = ('openai', 'anthropic', 'gemini', 'ollama', 'openai-compatible')
CLI = ('claude', 'codex', 'gemini', 'ollama')


def _has_review_text(text):
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            continue
        remaining = line.replace('[REDACTED PRIVATE KEY]', '').replace('[REDACTED]', '').strip(' \t`*#>-')
        if remaining and remaining.upper().rstrip(':') not in ('RISULTATI', 'LIMITI') and not ASSIGNMENT.fullmatch(remaining):
            return True
    return False


def emit(value):
    print(json.dumps(value, ensure_ascii=True, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='vibe-shield')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('scan', 'check'):
        p = sub.add_parser(name)
        p.add_argument('path', nargs='?', default='.')
        if name == 'scan':
            p.add_argument('--history', action='store_true', help='Scansiona tutta la storia Git disponibile')
    sub.add_parser('providers')
    p = sub.add_parser('review', help='Revisione consultiva, non sblocca il gate')
    p.add_argument('path', nargs='?', default='.')
    p.add_argument('--mode', required=True, choices=('api', 'cli'))
    p.add_argument('--provider', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--file', action='append', required=True, dest='files')
    p.add_argument('--endpoint')
    p.add_argument('--max-input-bytes', type=int, default=65536)
    p.add_argument('--max-output-tokens', type=int, default=2000)
    p.add_argument('--timeout', type=int, default=60)
    p.add_argument('--detail', choices=('concise', 'detailed'), default='concise',
                   help='Risposta concisa strutturata o revisione estesa')
    p.add_argument('--execute', action='store_true', help='Consenti la chiamata con i file selezionati; può avere costi')
    args = parser.parse_args(argv)
    try:
        root = resource_root()
        if args.command == 'providers':
            emit({'api': list(API), 'cli': {'claude': 'supported', 'ollama': 'unavailable: allegati automatici non isolati; usa API',
                  'codex': 'unavailable: isolamento strumenti non verificato',
                  'gemini': 'unavailable: isolamento strumenti non verificato'},
                  'model': 'Identificatore esplicito del provider, nessun fallback',
                  'live_provider_tests': 'non effettuati'})
            return 0
        target = Path(args.path).resolve(strict=True)
        if args.command in ('scan', 'check'):
            if not target.is_dir():
                raise ProviderError('Seleziona una cartella.')
            if args.command == 'scan':
                command = [sys.executable, str(root / 'scripts/secret_scan.py'), str(target)]
                if args.history:
                    command.append('--history=--all')
            else:
                command = [sys.executable, str(root / 'scripts/gate.py'), '--check']
            return subprocess.run(command, cwd=target).returncode
        if args.provider not in (API if args.mode == 'api' else CLI):
            raise ProviderError('Provider non supportato nella modalita scelta; consulta providers.')
        if not args.model.strip() or args.model.startswith('-') or any(ord(c) < 32 for c in args.model):
            raise ProviderError('Specifica un identificatore di modello valido.')
        if not 1 <= args.timeout <= 300 or not 1 <= args.max_output_tokens <= 32768:
            raise ProviderError('Timeout consentito 1–300 secondi; output 1–32768 token.')
        if args.endpoint and (args.mode != 'api' or args.provider not in ('ollama', 'openai-compatible')):
            raise ProviderError('Endpoint personalizzato ammesso solo per API Ollama/openai-compatible.')
        if args.endpoint:
            from .providers import _base_url
            _base_url(args.endpoint)
        files = collect(target, args.files, args.max_input_bytes)
        manifest = [{k: f[k] for k in ('path', 'sha256', 'bytes')} for f in files]
        common = {'schema_version': 1, 'mode': args.mode, 'provider': args.provider,
                  'requested_model': redact(args.model), 'files': manifest, 'detail': args.detail,
                  'gate_authorized': False, 'coverage': 'selected_files_only'}
        if not args.execute:
            emit(dict(common, status='preview', notice='Nessun invio. --execute autorizza la chiamata; '
                      'mascheramento a pattern non garantisce assenza di dati sensibili.',
                      endpoint=args.endpoint or ('configurazione CLI' if args.mode == 'cli' else args.provider)))
            return 0
        # Invalidate any prior approval before reviewing; never write a pass from AI output.
        begun = subprocess.run([sys.executable, str(root / 'scripts/gate.py'), 'write', 'begin'],
                               cwd=target, capture_output=True)
        if begun.returncode:
            raise ProviderError('Impossibile invalidare il gate precedente; revisione interrotta.')
        prompt = prompt_for(files, args.detail)
        started = time.monotonic()
        if args.mode == 'api':
            from .providers import run_api
            result = run_api(args.provider, args.model, prompt, endpoint=args.endpoint,
                             timeout=args.timeout, max_output_tokens=args.max_output_tokens)
        else:
            from .cli_providers import run_cli
            result = run_cli(args.provider, args.model, prompt, timeout=args.timeout,
                             max_output_tokens=args.max_output_tokens)
        after = collect(target, args.files, args.max_input_bytes)
        changed = [(f['path'], f['sha256']) for f in files] != [(f['path'], f['sha256']) for f in after]
        review = redact_output(result.text)
        unavailable = not _has_review_text(review)
        emit(dict(common, status='incomplete' if changed or not result.complete or unavailable else 'advisory',
                  returned_model=redact(result.model) if result.model else None, usage=result.usage,
                  duration_seconds=round(time.monotonic() - started, 3), repository_changed=changed,
                  review=review, review_redacted=review != result.text, response_segments=result.response_segments,
                  response_complete=result.complete, error=result.error or (
                      'Testo non disponibile dopo il mascheramento.' if unavailable else None)))
        return 3 if changed or not result.complete or unavailable else 0
    except (ProviderError, OSError, ValueError, RuntimeError) as error:
        message = str(error) if isinstance(error, ProviderError) else 'Operazione incompleta; verifica percorso e risorse locali.'
        emit({'status': 'incomplete', 'gate_authorized': False, 'error': message})
        return 3


if __name__ == '__main__':
    sys.exit(main())
