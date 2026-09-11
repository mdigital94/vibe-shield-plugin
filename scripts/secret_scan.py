#!/usr/bin/env python3
"""Deterministic known-format scan. Exit 0 clean, 2 findings, 3 incomplete."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from commit_scan import SCRIPTS, ScanError, git, secret, secret_content, sensitive, filtered


def run(args):
    target = Path(args.target).resolve()
    probe = subprocess.run(['git', '-C', str(target), 'rev-parse', '--show-toplevel'], capture_output=True)
    repo = Path(os.fsdecode(probe.stdout).strip()) if probe.returncode == 0 else None
    findings = []
    count = 0
    incomplete = False

    def inspect(name, data, revision=None):
        nonlocal count
        count += 1
        base = repo or target
        if secret(base, data, name) or sensitive(base, name):
            findings.append((revision, name))

    if args.history is not None:
        if repo is None:
            raise ScanError('La scansione storica richiede un repository Git.')
        incomplete = git(repo, 'rev-parse', '--is-shallow-repository').strip() == b'true'
        refs = git(repo, 'for-each-ref', '--format=%(objectname)').splitlines()
        tag_objects = set()
        tree_objects = set()
        blob_objects = set()
        for ref in refs:
            oid = ref.decode('ascii')
            kind = git(repo, 'cat-file', '-t', oid).strip()
            seen_tags = set()
            while kind == b'tag' and oid not in seen_tags:
                seen_tags.add(oid)
                tag_objects.add(oid)
                body = git(repo, 'cat-file', 'tag', oid)
                oid = body.split(b'\n', 1)[0].split(b' ', 1)[1].decode('ascii')
                kind = git(repo, 'cat-file', '-t', oid).strip()
            if kind == b'tree':
                tree_objects.add(oid)
            elif kind == b'blob':
                blob_objects.add(oid)
            elif kind != b'commit':
                incomplete = True
        revisions = git(repo, 'rev-list', '--all').splitlines()
        content_cache = {}
        checked = set()
        name_cache = {}
        if args.history != '--all':
            try:
                limit = int(args.history)
            except ValueError:
                raise ScanError('Limite storia non valido: usa un numero positivo o --all.')
            if limit <= 0:
                raise ScanError('Il limite della storia deve essere positivo.')
            incomplete = incomplete or len(revisions) > limit
            revisions = revisions[:limit]
        for revision in [rev.decode('ascii') for rev in revisions] + sorted(tree_objects):
            entries = git(repo, 'ls-tree', '-r', '-z', revision).split(b'\0')
            for entry in entries:
                if not entry:
                    continue
                meta, raw_name = entry.split(b'\t', 1)
                mode, kind, oid = meta.split()
                if kind != b'blob':
                    incomplete = True
                    continue
                name = os.fsdecode(raw_name)
                pair = (oid, raw_name)
                if pair in checked:
                    continue
                checked.add(pair)
                count += 1
                if oid not in content_cache:
                    content_cache[oid] = secret_content(repo, git(repo, 'cat-file', 'blob', oid.decode('ascii')))
                if name not in name_cache:
                    name_cache[name] = sensitive(repo, name)
                if name_cache[name] or (content_cache[oid] and filtered(repo, raw_name + b'\n')):
                    findings.append((revision, name))
        for oid in sorted(blob_objects):
            count += 1
            raw_oid = oid.encode('ascii')
            if raw_oid not in content_cache:
                content_cache[raw_oid] = secret_content(repo, git(repo, 'cat-file', 'blob', oid))
            if content_cache[raw_oid]:
                findings.append((oid, '<blob senza percorso>'))
        for kind, oid in [('commit', rev.decode('ascii')) for rev in revisions] + [('tag', oid) for oid in sorted(tag_objects)]:
            count += 1
            if secret_content(repo, git(repo, 'cat-file', kind, oid)):
                findings.append((oid, '<messaggio/metadati ' + kind + '>'))
    else:
        if not target.is_dir():
            raise ScanError('Cartella da controllare non disponibile.')
        if repo:
            # Always normalize to the project root; no silent partial repository scan.
            names = set(git(repo, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''}
            base = repo
        else:
            names = set()
            base = target
            for folder, dirs, files in os.walk(base):
                if any((Path(folder) / d).is_symlink() or d == '.git' for d in dirs):
                    incomplete = True
                dirs[:] = [d for d in dirs if d not in {'.git', '.vibe-shield'} and not (Path(folder) / d).is_symlink()]
                for name in files:
                    names.add(os.fsencode(str((Path(folder) / name).relative_to(base))))
        for raw_name in sorted(names):
            name = os.fsdecode(raw_name)
            path = base / name
            if not path.exists() and not path.is_symlink():
                continue  # Deleted files are not in the current working tree.
            if path.is_dir():
                incomplete = True
                continue
            if path.is_symlink():
                incomplete = True
                data = os.fsencode(os.readlink(path))
            else:
                data = path.read_bytes()
            inspect(name, data)

    for revision, name in findings[:60]:
        prefix = revision[:12] + ':' if revision else ''
        print(prefix + repr(name) + ': possibile segreto o nome sensibile (valore omesso)')
    if len(findings) > 60:
        print('Output limitato ai primi 60 risultati; tutti i file previsti sono stati esaminati.')
    print(f'File/versioni distinti esaminati: {count}; risultati: {len(findings)}; copertura scanner: {"incompleta" if incomplete else "completa per il perimetro dichiarato"}.')
    print('Perimetro: formati noti e nomi sensibili; working tree Git esclude file ignorati non tracciati. Non sostituisce la revisione semantica.')
    if incomplete:
        print('Controllo incompleto: estendi la storia con --history --all e verifica storia shallow, riferimenti non supportati, symlink, submodule o directory escluse separatamente.', file=sys.stderr)
        return 3
    return 2 if findings else 0


def main():
    # Normalize --history --all before argparse interprets it as another option.
    argv = sys.argv[1:]
    if argv[:2] == ['--history', '--all']:
        argv = ['--history=--all', *argv[2:]]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', default='.')
    parser.add_argument('--history', nargs='?', const='50')
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return 0 if error.code == 0 else 3
    try:
        return run(args)
    except (ScanError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, ScanError) else 'Lettura dei file non completata.'
        print('VIBE SHIELD: scansione incompleta. ' + message, file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
