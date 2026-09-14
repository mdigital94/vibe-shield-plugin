"""Locate the same audited scripts in a checkout or installed wheel."""
from pathlib import Path


def resource_root():
    bundled = Path(__file__).resolve().parent / '_resources'
    root = bundled if bundled.is_dir() else Path(__file__).resolve().parents[1]
    if not (root / 'scripts' / 'gate.py').is_file():
        raise RuntimeError('Risorse Vibe Shield mancanti; reinstalla il pacchetto.')
    return root
