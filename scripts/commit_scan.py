#!/usr/bin/env python3
"""Scan the index Git will commit; never print matched credential values."""
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
NAME_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (SCRIPTS / "patterns-files.grep").read_text().splitlines() if p)


class ScanError(Exception):
    pass


def git(repo, *args, allowed=(0,)):
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args], capture_output=True)
    if result.returncode not in allowed:
        raise ScanError('Git non ha completato il controllo dello stage.')
    return result.stdout


def filtered(repo, data, placeholders=False):
    # Constant shell source, untrusted text only on stdin, never as shell code.
    pipeline = 'vs_filter_placeholders | vs_filter_allowlist' if placeholders else 'vs_filter_allowlist'
    result = subprocess.run(
        ['bash', '-c', '. "$1"; ' + pipeline, 'vibe-shield', str(SCRIPTS / 'lib.sh')],
        cwd=repo, input=data, capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ScanError('Filtro dei risultati non disponibile.')
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)
    return bool(result.stdout.strip())


def grep(data, pattern, flags=()):
    result = subprocess.run(['grep', *flags, '-E', '-f', str(SCRIPTS / pattern)],
                            input=data, capture_output=True)
    if result.returncode not in (0, 1):
        raise ScanError('Pattern di scansione non validi o non leggibili.')
    return result.stdout


def sensitive(repo, name):
    if Path(name).name.lower() in ('.env.example', '.env.sample', '.env.template', '.env.dist'):
        return False  # Only the filename exception; content is still scanned.
    return any(pattern.search(name) for pattern in NAME_PATTERNS) and filtered(repo, os.fsencode(name) + b'\n')


def secret_content(repo, data):
    matches = grep(data, 'patterns-exact.grep', ('-a', '-o'))
    return bool(matches) and filtered(repo, matches, True)


def secret(repo, data, name):
    return secret_content(repo, data) and filtered(repo, os.fsencode(name) + b'\n')


def worktree_needed(command):
    try:
        tokens = shlex.split(command)
    except ValueError:
        raise ScanError('Comando non interpretabile: separa git add e git commit.')
    # Extra worktree scan is conservative for compound add and pathspec commits.
    if 'add' in tokens:
        return True, '--force' in tokens or any(t.startswith('-') and not t.startswith('--') and 'f' in t[1:] for t in tokens)
    if 'commit' not in tokens:
        return False, False
    args = tokens[tokens.index('commit') + 1:]
    skip = False
    value_options = {'-m', '--message', '-F', '--file', '-C', '--reuse-message', '-c', '--reedit-message', '--author', '--date', '--cleanup', '--trailer'}
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in value_options:
            skip = True
            continue
        if arg.startswith(('-m', '-F')) and len(arg) > 2:
            continue
        if arg in ('--all', '--include', '--only', '--') or arg.startswith('--pathspec'):
            return True, False
        if arg.startswith('-') and not arg.startswith('--') and any(c in arg[1:] for c in 'aio'):
            return True, False
        if not arg.startswith('-'):
            return True, False
    return False, False


def scan(command):
    repo = Path(os.fsdecode(git(Path.cwd(), 'rev-parse', '--show-toplevel')).strip())
    entries = git(repo, 'ls-files', '--stage', '-z').split(b'\0')
    bad = set()
    hits = set(git(repo, 'grep', '--cached', '-a', '-l', '-z', '-E', '-f', str(SCRIPTS / 'patterns-exact.grep'), '--', '.', allowed=(0, 1)).split(b'\0'))
    for entry in entries:
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.split()
        name = os.fsdecode(raw_name)
        if stage != b'0':
            raise ScanError('Stage con conflitti: risolvili prima del commit.')
        if mode == b'160000':
            raise ScanError('Submodule presente: controllo separato necessario, copertura incompleta.')
        if sensitive(repo, name):
            bad.add(name)
        if raw_name in hits:
            data = git(repo, 'cat-file', 'blob', oid.decode('ascii'))
            if secret(repo, data, name):
                bad.add(name)
    extra, force = worktree_needed(command)
    if extra:
        names = git(repo, 'ls-files', '--cached', '--others', '-z', *([] if force else ['--exclude-standard']))
        for raw_name in set(names.split(b'\0')) - {b''}:
            name = os.fsdecode(raw_name)
            path = repo / name
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_dir():
                raise ScanError('Directory annidata non scansionabile: separa le operazioni Git.')
            if sensitive(repo, name):
                bad.add(name)
            data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
            if secret(repo, data, name):
                bad.add(name)
    if bad:
        print('🛑 VIBE SHIELD: commit BLOCCATO. File sensibili o possibili segreti nella versione da committare:', file=sys.stderr)
        for name in sorted(bad):
            print('  ' + repr(name), file=sys.stderr)
        print('Rimuovi i segreti dallo stage, usa variabili d’ambiente e aggiungi nuovamente i file corretti. Se la chiave era reale ed esposta, revocala.', file=sys.stderr)
        return 2
    return 0


def main():
    if os.environ.get('VIBE_SHIELD_SKIP') == '1':
        return 0
    try:
        return scan(sys.argv[1] if len(sys.argv) > 1 else '')
    except (ScanError, OSError, ValueError) as error:
        # Avoid echoing paths, command arguments or file contents from exceptions.
        message = str(error) if isinstance(error, ScanError) else 'Errore nella lettura dei file.'
        print('🛑 VIBE SHIELD: controllo commit incompleto. ' + message, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
