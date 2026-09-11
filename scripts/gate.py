#!/usr/bin/env python3
"""Local publication guard; content-bound cache, not an integrity/security boundary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

PLUGIN = Path(__file__).resolve().parents[1]
GENERATED_REPORTS = {b'.vibe-shield/status.json', b'.vibe-shield/audit-start.json', b'.vibe-shield/report.md'}


def block(message):
    raise ValueError(message)


def git(root, *args, optional=False):
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args], capture_output=True)
    if result.returncode and not optional:
        block('Impossibile leggere lo stato Git; controllo incompleto.')
    return result.stdout if not result.returncode else b''


def root_for(path):
    path = Path(path).resolve(strict=True)
    top = git(path, 'rev-parse', '--show-toplevel', optional=True)
    return Path(os.fsdecode(top).strip()).resolve() if top else path


def fingerprint(root):
    digest = hashlib.sha256()
    def add(label, value):
        digest.update(os.fsencode(label) + b'\0' + str(len(value)).encode() + b'\0' + value)
    add('root', os.fsencode(root))
    if git(root, 'rev-parse', '--show-toplevel', optional=True):
        add('head', git(root, 'rev-parse', '--verify', 'HEAD', optional=True))
        add('refs', git(root, 'show-ref', optional=True))
        add('index', git(root, 'ls-files', '--stage', '-z'))
        add('git-config', git(root, 'config', '--local', '--null', '--list'))
        names = set(git(root, 'ls-files', '-z').split(b'\0'))
        names.update(git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'))
        # Deploy tools may publish ignored build outputs. Include them in cache identity.
        ignored = git(root, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z').split(b'\0')
        dependencies = {'node_modules', '.venv', 'venv', 'vendor', '__pycache__', '.cache'}
        names.update(name for name in ignored if not dependencies.intersection(Path(os.fsdecode(name)).parts))
    else:
        names = {os.fsencode(p.relative_to(root)) for p in root.rglob('*')
                 if p.is_file() or p.is_symlink()}
    # Reports/status are generated output. Allowlist remains an input even when ignored.
    names.add(b'.vibe-shield/allowlist')
    names.add(b'.vibe-shield/allowlist.txt')
    for name in sorted(names):
        if not name or name in GENERATED_REPORTS:
            continue
        path = root / os.fsdecode(name)
        if path.is_symlink():
            if not path.is_file():
                block('Link simbolico a directory o target mancante: controllo incompleto.')
            add(name, os.fsencode(os.readlink(path)))
            # A symlink target can change independently of the link text.
            if path.is_file():
                add(name + b':target', path.read_bytes())
        elif path.is_file():
            add(name, path.read_bytes())
            add(name + b':mode', str(path.stat().st_mode).encode())
        elif path.is_dir():
            block('Directory/submodule tracciata non supportata dal gate: controllo incompleto.')
        else:
            add(name, b'<missing>')
    for directory in ('scripts', 'skills', 'agents', 'hooks', 'templates', '.claude-plugin'):
        for path in sorted((PLUGIN / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                add(str(path.relative_to(PLUGIN)), path.read_bytes())
    return digest.hexdigest()


def status_path(root):
    folder = root / '.vibe-shield'
    if folder.is_symlink():
        block('La directory del gate non può essere un collegamento simbolico.')
    return folder / 'status.json'


def check(root):
    try:
        data = json.loads(status_path(root).read_text())
        age = time.time() - data['epoch']
        counts = data['findings']
        valid = (data['version'] == 2 and data['result'] == 'pass'
                 and data['scope'] == 'full' and data['complete'] is True
                 and data['root'] == str(root) and 0 <= age < 1800
                 and all(type(counts[k]) is int and counts[k] >= 0 for k in ('critici', 'alti', 'medi', 'bassi'))
                 and not any(counts[k] for k in ('critici', 'alti', 'medi'))
                 and data['fingerprint'] == fingerprint(root))
    except (KeyError, TypeError, OSError, ValueError):
        valid = False
    if not valid:
        block('Pubblicazione BLOCCATA: audit assente, incompleto, scaduto o contenuti cambiati. Esegui /pre-deploy.')


def write(args, root):
    if args.result == 'begin':
        path = status_path(root)
        epoch = time.time()
        if args.reuse:
            check(root)
            epoch = json.loads(path.read_text())['epoch']
        path.parent.mkdir(exist_ok=True)
        atomic_write(path, {'version': 2, 'result': 'incomplete'})
        atomic_write(path.parent / 'audit-start.json', {'fingerprint': fingerprint(root), 'epoch': epoch})
        print('Audit iniziato; precedente gate invalidato.')
        return
    counts = args.counts
    valid_counts = len(counts) == 4 and all(re.fullmatch(r'[0-9]+', n) for n in counts)
    passing = args.result == 'pass'
    valid = valid_counts and (not passing or (args.scope == 'full' and args.complete and not any(int(n) for n in counts[:3])))
    # Invalidate first, also for malformed attempted PASS. Never preserve stale approval.
    path = status_path(root)
    path.parent.mkdir(exist_ok=True)
    payload = {'version': 2, 'result': 'incomplete', 'epoch': int(time.time()), 'root': str(root)}
    atomic_write(path, payload)
    if not valid:
        block('Gate invalidato: PASS richiede conteggi validi, --scope full --complete e zero problemi medi/alti/critici.')
    payload.update(result=args.result, scope=args.scope, complete=args.complete,
                   findings=dict(zip(('critici', 'alti', 'medi', 'bassi'), map(int, counts))))
    if passing:
        current = fingerprint(root)
        try:
            started = json.loads((path.parent / 'audit-start.json').read_text())
            same = started['fingerprint'] == current and 0 <= time.time() - started['epoch'] < 1800
        except (OSError, ValueError, KeyError, TypeError):
            same = False
        if not same:
            block('Gate invalidato: manca begin valido o contenuti cambiati durante audit; ripeti il controllo.')
        payload['fingerprint'] = current
        payload['epoch'] = started['epoch']
    atomic_write(path, payload)
    print('Gate scritto: ' + args.result + ' (30 minuti E contenuti invariati).')


def atomic_write(path, payload):
    fd, temporary = tempfile.mkstemp(prefix='.status-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command_info(tokens, cwd):
    if not tokens:
        return None, cwd
    executable = Path(tokens[0]).name
    args = tokens[1:]
    if executable == 'git':
        location = cwd
        while args and args[0].startswith('-'):
            option = args.pop(0)
            if option == '-C' and args:
                location = (location / args.pop(0)).resolve()
            elif option.startswith('-C') and len(option) > 2:
                location = (location / option[2:]).resolve()
            elif option in ('--no-pager', '--paginate', '--no-optional-locks'):
                continue
            else:
                # -c can change aliases/hooks; --git-dir/work-tree changes authority.
                return 'ambiguous', location
        return (args[0] if args else None), location
    deploy = {'vercel', 'surge'}
    sequences = {'netlify': ('deploy',), 'firebase': ('deploy',), 'wrangler': ('deploy', 'publish'),
                 'fly': ('deploy',), 'flyctl': ('deploy',), 'railway': ('up',), 'render': ('deploy',),
                 'npm': ('publish',), 'heroku': ('deploy', 'releases:create'), 'amplify': ('publish',)}
    if executable in deploy or (executable in sequences and any(a in sequences[executable] for a in args)):
        return 'deploy', cwd
    if (executable == 'gh' and (args[:2] in (['repo', 'create'], ['release', 'create']))) or (executable == 'gcloud' and args[:2] == ['app', 'deploy']) or (executable == 'aws' and args[:2] == ['s3', 'sync']):
        return 'deploy', cwd
    return None, cwd


def validate_prerelease(tokens, root):
    """Authorize only an existing, audited tag and inline metadata on its GitHub origin."""
    args = tokens[3:]
    if not args or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', args[0]):
        block('Prerelease: tag letterale obbligatorio.')
    tag, options = args[0], {}
    index = 1
    while index < len(args):
        option = args[index]
        if option in options or option not in ('--verify-tag', '--prerelease', '--repo', '--notes', '--title'):
            block('Prerelease: opzione o asset non supportato.')
        if option in ('--verify-tag', '--prerelease'):
            options[option] = True
            index += 1
        else:
            if index + 1 >= len(args) or args[index + 1].startswith('-'):
                block('Prerelease: valore letterale mancante.')
            options[option] = args[index + 1]
            index += 2
    if not all(key in options for key in ('--verify-tag', '--prerelease', '--repo', '--notes')):
        block('Prerelease: richiesti --verify-tag --prerelease --repo --notes.')
    origin = git(root, 'remote', 'get-url', 'origin').decode().strip()
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', origin)
    if not match or options['--repo'] != 'https://github.com/' + match.group(1):
        block('Prerelease: repository esplicito diverso da origin GitHub.')
    if os.environ.get('GH_HOST', 'github.com') != 'github.com':
        block('Prerelease: host GitHub alternativo non supportato.')
    # The explicit HTTPS --repo fixes gh repository selection, including GH_REPO overrides.
    ref = 'refs/tags/' + tag
    git(root, 'check-ref-format', ref)
    object_id = git(root, 'rev-parse', '--verify', '--end-of-options', ref).strip()
    commit = git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').strip()
    if commit != git(root, 'rev-parse', '--verify', 'HEAD').strip():
        block('Prerelease: il tag non identifica HEAD sottoposto ad audit.')
    if git(root, 'status', '--porcelain', '--untracked-files=no'):
        block('Prerelease: file tracciati modificati; commit e nuovo audit necessari.')
    remote = git(root, 'ls-remote', '--exit-code', '--tags', 'origin', ref).splitlines()
    if remote != [object_id + b'\t' + ref.encode()]:
        block('Prerelease: tag remoto assente o diverso dal tag locale.')
    metadata = (options['--notes'] + '\n' + options.get('--title', '') + '\n' + tag).encode()
    result = subprocess.run(['grep', '-a', '-q', '-E', '-f', str(PLUGIN / 'scripts/patterns-exact.grep')],
                            input=metadata, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 1:
        block('Prerelease: metadati con possibili segreti o scanner fallito.')
    return object_id.decode()


def dispatch(command, cwd, force=False):
    # Shell is not parsed as a programming language: only simple literal commands are authorized.
    hint = re.search(r'\b(push|commit|deploy|publish|vercel|surge|railway|releases:create)\b', command)
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>')
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        block('Comando non analizzabile: separa commit e pubblicazione in comandi semplici.')
    hint = re.search(r'\b(push|commit|deploy|publish|vercel|surge|railway|releases:create|gh|aws)\b', ' '.join(tokens))
    if not hint and not force:
        return
    if any(t and all(c in ';&|()<>' for c in t) for t in tokens) or '\n' in command or re.search(r'[$`]', command):
        block('Comando composto/dinamico bloccato: esegui modifica, commit e pubblicazione separatamente.')
    kind, location = command_info(tokens, cwd)
    if kind == 'commit' and not force:
        # Global -C was resolved above; prevent applying it twice.
        index = tokens.index('commit')
        normalized = shlex.join(['git', *tokens[index:]])
        result = subprocess.run([str(PLUGIN / 'scripts/guard-commit.sh'), normalized], cwd=location)
        if result.returncode:
            block('Commit bloccato dal controllo segreti.')
        return
    if kind not in ('push', 'deploy'):
        if kind in ('status', 'log', 'show', 'diff', 'grep', 'ls-files', 'rev-parse', 'rev-list', 'describe') or (tokens and Path(tokens[0]).name in ('cat', 'rg', 'grep', 'ls', 'head', 'tail', 'printf', 'echo')):
            return
        # A command containing publication syntax behind env/shell/functions cannot be trusted.
        if hint or force:
            block('Comando di pubblicazione ambiguo/non supportato: usa un comando diretto e letterale.')
        return
    prerelease = [Path(tokens[0]).name, *tokens[1:3]] == ['gh', 'release', 'create']
    if kind == 'deploy' and not prerelease:
        allowed = {('vercel',), ('vercel', 'deploy'), ('vercel', '--prod'), ('vercel', 'deploy', '--prod'),
                   ('netlify', 'deploy'), ('netlify', 'deploy', '--prod'), ('firebase', 'deploy'),
                   ('wrangler', 'deploy'), ('wrangler', 'publish'), ('fly', 'deploy'), ('flyctl', 'deploy'),
                   ('railway', 'up'), ('render', 'deploy'), ('npm', 'publish'), ('heroku', 'deploy'),
                   ('heroku', 'releases:create'), ('gcloud', 'app', 'deploy'), ('amplify', 'publish'), ('surge',)}
        if tuple([Path(tokens[0]).name, *tokens[1:]]) not in allowed:
            block('Opzioni/percorso di deploy non supportati: impossibile determinare i contenuti pubblicati.')
    root = root_for(location)
    check(root)
    extra = [validate_prerelease(tokens, root)] if prerelease else []
    if kind == 'push':
        # Include explicit source expressions, including detached/unreferenced commit IDs.
        for token in tokens[tokens.index('push') + 1:]:
            if token.startswith('-'):
                continue
            source = token.lstrip('+').split(':', 1)[0]
            if not source:
                continue
            object_id = git(root, 'rev-parse', '--verify', '--end-of-options', source, optional=True).strip()
            if object_id:
                # Keep the original object: peeling a tag would omit its metadata.
                extra.append(object_id.decode())
    scan_publication(root, extra)
    check(root)  # Detect concurrent changes during scanning.


def scan_publication(root, extra):
    if git(root, 'rev-parse', '--show-toplevel', optional=True):
        files = set(git(root, 'ls-files', '-z').split(b'\0'))
        files.update(git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'))
        for name in files:
            if not name or name in GENERATED_REPORTS:
                continue
            path = root / os.fsdecode(name)
            if not path.is_file():
                continue
            result = subprocess.run(['grep', '-a', '-l', '-E', '-f', str(PLUGIN / 'scripts/patterns-exact.grep'), '--', str(path)], capture_output=True)
            if result.returncode == 0:
                block('Possibili segreti nei file da pubblicare; esegui /secrets-scan.')
            if result.returncode != 1:
                block('Scanner file fallito: pubblicazione bloccata.')
        if git(root, 'rev-parse', '--is-shallow-repository').strip() == b'true':
            block('Storia Git incompleta (shallow): impossibile validare la pubblicazione.')
        object_ids = git(root, 'rev-list', '--objects', '--all', '--no-object-names', *extra).splitlines()
        scan_objects(root, sorted(set(object_ids)))
    else:
        block('Pubblicazione fuori da Git non supportata dal gate automatico.')


def scan_objects(root, object_ids):
    """Scan each reachable blob and commit/tag metadata once; never print object data."""
    command = ['git', '--no-replace-objects', '-C', str(root), 'cat-file', '--batch']
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as process:
        for object_id in object_ids:
            process.stdin.write(object_id + b'\n')
            process.stdin.flush()
            fields = process.stdout.readline().split()
            if len(fields) != 3 or fields[0] != object_id or not fields[2].isdigit():
                block('Lettura oggetti Git incompleta: pubblicazione bloccata.')
            object_type, remaining = fields[1], int(fields[2])
            if object_type == b'tree':
                entries = git(root, 'ls-tree', '-z', object_id.decode()).split(b'\0')
                if any(entry.startswith(b'160000 ') for entry in entries):
                    block('Submodule nella storia Git: controllo separato necessario, copertura incompleta.')
            if object_type not in (b'blob', b'commit', b'tag', b'tree'):
                block('Tipo oggetto Git non supportato: pubblicazione bloccata.')
            with tempfile.TemporaryFile() as content:
                while remaining:
                    chunk = process.stdout.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        block('Oggetto Git troncato: pubblicazione bloccata.')
                    if object_type != b'tree':
                        content.write(chunk)
                    remaining -= len(chunk)
                if process.stdout.read(1) != b'\n':
                    block('Formato oggetto Git non valido: pubblicazione bloccata.')
                if object_type != b'tree':
                    content.seek(0)
                    result = subprocess.run(['grep', '-a', '-q', '-E', '-f',
                                             str(PLUGIN / 'scripts/patterns-exact.grep')],
                                            stdin=content, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                    if result.returncode == 0:
                        block('Possibili segreti negli oggetti Git o nei messaggi commit/tag. Esegui /secrets-scan.')
                    if result.returncode != 1:
                        block('Scanner oggetti Git fallito: pubblicazione bloccata.')
        process.stdin.close()
        process.wait()
        if process.returncode:
            block('Lettura storia Git fallita: pubblicazione bloccata.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('dispatch', 'publish', 'write'), nargs='?')
    parser.add_argument('result', nargs='?')
    parser.add_argument('counts', nargs='*')
    parser.add_argument('--scope', default='partial', choices=('full', 'partial'))
    parser.add_argument('--complete', action='store_true')
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check(root_for(Path.cwd()))
    elif args.action == 'write':
        if args.result not in ('pass', 'fail', 'incomplete', 'begin'):
            args.result = 'incomplete'
        write(args, root_for(Path.cwd()))
    elif args.action == 'dispatch':
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or not isinstance(data.get('tool_input', {}), dict):
            block('Input hook non valido: controllo incompleto.')
        command = data.get('tool_input', {}).get('command', '')
        if not isinstance(command, str):
            block('Comando hook non valido: controllo incompleto.')
        dispatch(command, Path(data.get('cwd') or os.getcwd()).resolve())
    elif args.action == 'publish':
        dispatch(args.result or 'git push', Path.cwd(), force=True)
    else:
        parser.error('azione richiesta')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as exc:
        print('VIBE SHIELD: ' + str(exc), file=sys.stderr)
        sys.exit(2)
