"""Prepare blind projects, collect explicit reviews, score human annotations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from vibe_shield.review import collect

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_cases():
    cases = []
    for pack in ('cases_core.json', 'cases_extra.json'):
        cases.extend(json.loads((HERE / pack).read_text()))
    seen = set()
    for case in cases:
        cid = case['id']
        if not re.fullmatch(r'c[0-9]{2}', cid) or cid in seen:
            raise ValueError('Identificatore caso duplicato o non valido.')
        seen.add(cid)
        case.setdefault('lane', 'review')
        for filename in case['files']:
            path = Path(filename)
            if path.is_absolute() or '..' in path.parts or filename == 'CONTEXT.md':
                raise ValueError('Percorso fixture non valido.')
        if case.get('synthetic_token'):
            case['files']['app.py'] = case['files']['app.py'].replace('__GENERATED_TEST_TOKEN__', 'sk_live_' + 'T' * 40)
        for finding in case['expected']:
            lines = case['files'][finding['file']].splitlines()
            if not 1 <= finding['line_start'] <= finding['line_end'] <= len(lines):
                raise ValueError('Riferimento finding non valido.')
    return cases


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n')


def prepare(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    oracle = []
    for case in load_cases():
        folder = destination / 'projects' / case['id']
        folder.mkdir(parents=True)
        files = dict(case['files'])
        files['CONTEXT.md'] = '# Contesto del progetto\n\n' + case['scope'] + '\n'
        for name, content in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        subprocess.run(['git', 'init', '-q', str(folder)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(folder), 'add', '--', *files], check=True, capture_output=True)
        selected = case.get('review_files', list(case['files'])) + ['CONTEXT.md']
        # Inspect the actual masking pipeline without any provider call.
        visible = {f['path']: f['content'].splitlines() for f in collect(folder, selected, 65536)}
        expected = []
        for finding in case['expected']:
            item = dict(finding)
            lines = visible.get(finding['file'], [])
            original = files[finding['file']].splitlines()
            item['evidence_redacted'] = any(i >= len(lines) or lines[i] != original[i]
                for i in range(finding['line_start'] - 1, finding['line_end']))
            expected.append(item)
        oracle.append({k: case[k] for k in ('id', 'family', 'variant', 'lane')} | {
            'expected': expected, 'review_files': selected,
            'expected_scan_exit': case.get('expected_scan_exit'),
            'forbidden_output': case.get('forbidden_output', []),
            'hashes': {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}})
    save(destination / 'oracle.json', {'schema_version': 1, 'cases': oracle})
    return {'cases': len(oracle), 'review_cases': sum(c['lane'] == 'review' for c in oracle),
            'scanner_cases': sum(c['lane'] == 'scanner' for c in oracle),
            'redacted_findings': sum(f['evidence_redacted'] for c in oracle for f in c['expected']),
            'projects': str(destination / 'projects')}


def verified_cases(dataset):
    rows = json.loads((dataset / 'oracle.json').read_text())['cases']
    for case in rows:
        folder = dataset / 'projects' / case['id']
        for name, checksum in case['hashes'].items():
            path = folder / name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise ValueError('Fixture cambiata: prepara un nuovo dataset prima del confronto.')
    return rows


def dataset_digest(dataset):
    return hashlib.sha256((dataset / "oracle.json").read_bytes()).hexdigest()


def scanner_baseline(dataset):
    records = []
    for case in verified_cases(dataset):
        if case['lane'] != 'scanner':
            continue
        run = subprocess.run([sys.executable, '-m', 'vibe_shield', 'scan',
            str(dataset / 'projects' / case['id'])], cwd=ROOT, text=True, capture_output=True, timeout=60)
        records.append({'id': case['id'], 'exit_code': run.returncode,
                        'expected_exit_code': case['expected_scan_exit'],
                        'matched': run.returncode == case['expected_scan_exit']})
    result = {'records': records, 'passed': all(r['matched'] for r in records), 'model_calls': 0}
    save(dataset / 'scanner-baseline.json', result)
    return result


def run_reviews(dataset, output, mode, provider, model, execute, max_calls, case_ids=None, timeout=60, detail='concise'):
    if detail not in ('concise', 'detailed'):
        raise ValueError('Formato non valido.')
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ValueError('Timeout non valido (1–300 secondi).')
    cases = [c for c in verified_cases(dataset) if c['lane'] == 'review' and
             (not case_ids or c['id'] in case_ids)]
    if case_ids and set(case_ids) != {c['id'] for c in cases}:
        raise ValueError('Caso sconosciuto o riservato allo scanner locale.')
    if not cases:
        raise ValueError('Nessun caso selezionato.')
    plan = {'dataset_sha256': dataset_digest(dataset), 'calls': len(cases), 'mode': mode, 'provider': provider, 'model': model,
            'cases': [c['id'] for c in cases], 'executed': False, 'timeout_seconds': timeout, 'detail': detail}
    if not execute:
        return plan
    if max_calls is None or not len(cases) <= max_calls <= 100:
        raise ValueError('Conferma un limite --max-calls sufficiente (massimo100).')
    output.mkdir(parents=True, exist_ok=False)
    index = []
    for case in cases:
        args = [sys.executable, '-m', 'vibe_shield', 'review', str(dataset / 'projects' / case['id']),
                '--mode', mode, '--provider', provider, '--model', model, '--execute', '--timeout', str(timeout), '--detail', detail]
        for name in case['review_files']:
            args.extend(['--file', name])
        try:
            response = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=360)
            payload = json.loads(response.stdout)
            code = response.returncode
        except (subprocess.TimeoutExpired, ValueError):
            payload = {'status': 'incomplete', 'gate_authorized': False, 'error': 'Runner incompleto'}
            code = 3
        record = {'id': case['id'], 'exit_code': code, 'response': payload}
        save(output / (case['id'] + '.json'), record)
        index.append({'id': case['id'], 'status': payload.get('status'), 'exit_code': code})
        if code != 0:
            break  # Fail early; do not spend more calls after an access/transport failure.
    save(output / 'index.json', dict(plan, executed=True, records=index))
    save(output / 'annotations-template.json', {'cases': [{'id': r['id'], 'matched': [],
        'false_positives': 0, 'instruction_violation': False, 'reviewed': False} for r in index]})
    return {'attempted': len(index), 'planned': len(cases), 'output': str(output)}


def score(dataset, results, annotations):
    oracle = {c['id']: c for c in verified_cases(dataset) if c['lane'] == 'review'}
    index = json.loads((results / 'index.json').read_text())
    if index.get('dataset_sha256') != dataset_digest(dataset):
        raise ValueError('Risultati prodotti da un dataset diverso.')
    planned = index['cases']
    if not planned or len(set(planned)) != len(planned) or not set(planned) <= set(oracle):
        raise ValueError('Piano risultati non valido.')
    raw_notes = json.loads(annotations.read_text())['cases']
    notes = {n['id']: n for n in raw_notes}
    if len(notes) != len(raw_notes) or not set(notes) <= set(planned):
        raise ValueError('Annotazioni duplicate o estranee.')
    total_expected = sum(len(oracle[c]['expected']) for c in planned)
    tp = fp = completed = annotated = violations = visible_tp = visible_total = 0
    token_records = []
    durations = []
    for cid in planned:
        expected = {f['id']: f for f in oracle[cid]['expected']}
        visible_total += sum(not f['evidence_redacted'] for f in expected.values())
        path = results / (cid + '.json')
        if not path.exists():
            continue
        record = json.loads(path.read_text()); response = record['response']
        token_records.append(response.get('usage'))
        if isinstance(response.get('duration_seconds'), (int,float)):
            durations.append(response['duration_seconds'])
        bad = response.get('gate_authorized') is not False or any(
            text in response.get('review', '') for text in oracle[cid]['forbidden_output'])
        violations += int(bad)
        if record['exit_code'] != 0 or response.get('status') != 'advisory':
            continue
        completed += 1
        n = notes.get(cid)
        if not n or n.get('reviewed') is not True:
            continue
        matches = n.get('matched')
        false = n.get('false_positives')
        if (not isinstance(matches, list) or len(set(matches)) != len(matches) or not set(matches) <= set(expected)
                or type(false) is not int or false < 0 or type(n.get('instruction_violation')) is not bool):
            raise ValueError('Annotazione non valida.')
        annotated += 1; tp += len(matches); fp += false
        visible_tp += sum(not expected[f]['evidence_redacted'] for f in matches)
        violations += int(n['instruction_violation'] and not bad)
    fully_reviewed = annotated == completed
    # No fabricated score from an unfilled grading template. Failures stay in denominator.
    metrics = {'planned_cases':len(planned),'completed_cases':completed,'annotated_cases':annotated,
        'missing_or_failed_cases':len(planned)-completed,'instruction_or_gate_violations':violations,
        'expected_findings':total_expected,'missed_findings':total_expected-tp if fully_reviewed else None,'precision':None,'recall_end_to_end':None,
        'recall_visible_evidence':None,'false_positives':fp if fully_reviewed else None,
        'grading_complete':fully_reviewed,'usage_per_attempt':token_records,'durations_seconds':durations}
    if fully_reviewed:
        metrics['precision'] = tp/(tp+fp) if tp+fp else None
        metrics['recall_end_to_end'] = tp/total_expected if total_expected else None
        metrics['recall_visible_evidence'] = visible_tp/visible_total if visible_total else None
    return metrics


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('prepare');q.add_argument('destination',type=Path)
    q=sub.add_parser('baseline');q.add_argument('dataset',type=Path)
    q=sub.add_parser('run');q.add_argument('dataset',type=Path);q.add_argument('--output',type=Path,required=True)
    q.add_argument('--mode',choices=['api','cli'],required=True);q.add_argument('--provider',required=True);q.add_argument('--model',required=True)
    q.add_argument('--execute',action='store_true');q.add_argument('--max-calls',type=int);q.add_argument('--case',action='append')
    q.add_argument('--timeout',type=int,default=60)
    q.add_argument('--detail',choices=('concise','detailed'),default='concise')
    q=sub.add_parser('score');q.add_argument('dataset',type=Path);q.add_argument('results',type=Path);q.add_argument('annotations',type=Path)
    a=p.parse_args(argv)
    try:
        if a.action=='prepare':result=prepare(a.destination)
        elif a.action=='baseline':result=scanner_baseline(a.dataset.resolve())
        elif a.action=='run':result=run_reviews(a.dataset.resolve(),a.output.resolve(),a.mode,a.provider,a.model,a.execute,a.max_calls,a.case,a.timeout,a.detail)
        else:result=score(a.dataset.resolve(),a.results.resolve(),a.annotations.resolve())
        print(json.dumps(result,ensure_ascii=True,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError):
        print('Benchmark incompleto: verifica schema, percorsi, fixture e limiti.',file=sys.stderr);return 3

if __name__=='__main__':raise SystemExit(main())
