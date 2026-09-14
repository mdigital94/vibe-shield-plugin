"""Validate authored toy projects and benchmark accounting, not model quality."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmarks.runner import dataset_digest, load_cases, prepare, run_reviews, save, scanner_baseline, score, verified_cases


def implementation(family, variant):
    case = next(c for c in load_cases() if c['family'] == family and c['variant'] == variant)
    namespace = {'__name__': 'fixture'}
    exec(compile(case['files']['app.py'], case['id']+'/app.py', 'exec'), namespace)
    return namespace


class ExtraFixtureTests(unittest.TestCase):
    def test_html_injection_and_escaping(self):
        payload='<img src=x onerror=alert(1)>'
        self.assertIn(payload,implementation('html-output','vulnerable')['render'](payload))
        self.assertNotIn('<img',implementation('html-output','safe')['render'](payload))

    def test_redirect_destination_policy(self):
        bad='https://untrusted.example.invalid/'
        self.assertEqual(implementation('redirect','vulnerable')['destination'](bad),bad)
        safe=implementation('redirect','safe')['destination']
        for target in (bad,'//untrusted.example.invalid','/\\untrusted.example.invalid','/x\r\nOther: bad'):
            self.assertEqual(safe(target),'/')
        self.assertEqual(safe('/account'),'/account')

    def test_session_identity_cannot_be_changed_without_signature(self):
        key=b'synthetic-test-key-not-a-credential'
        encoded=base64.urlsafe_b64encode(json.dumps({'user':'admin'}).encode()).decode()
        self.assertEqual(implementation('session-integrity','vulnerable')['session_user'](encoded,key),'admin')
        safe=implementation('session-integrity','safe')['session_user']
        self.assertIsNone(safe(encoded+'.'+'0'*64,key))
        signature=hmac.new(key,encoded.encode(),hashlib.sha256).hexdigest()
        self.assertEqual(safe(encoded+'.'+signature,key),'admin')

    def test_csrf_requires_session_token(self):
        request={'method':'POST'};session={'user':'u','csrf':'test-csrf'}
        self.assertTrue(implementation('csrf','vulnerable')['can_update'](request,session))
        safe=implementation('csrf','safe')['can_update']
        self.assertFalse(safe(request,session))
        self.assertTrue(safe(dict(request,csrf='test-csrf'),session))

    def test_password_is_absent_from_safe_log(self):
        secret='synthetic-password'
        self.assertIn(secret,implementation('credential-logging','vulnerable')['log_attempt']('u',secret))
        self.assertNotIn(secret,implementation('credential-logging','safe')['log_attempt']('u',secret))

    def test_cors_does_not_authorize_arbitrary_origin(self):
        origin='https://untrusted.example.invalid'
        self.assertEqual(implementation('cors','vulnerable')['response_headers'](origin)['Access-Control-Allow-Origin'],origin)
        safe=implementation('cors','safe')['response_headers']
        self.assertNotIn('Access-Control-Allow-Origin',safe(origin))
        self.assertEqual(safe('https://portal.example.invalid')['Access-Control-Allow-Credentials'],'true')


class BenchmarkRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.dataset=Path(cls.tmp.name)/'dataset'
        cls.summary=prepare(cls.dataset)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_thirty_cases_answers_separate_and_canary_not_selected(self):
        self.assertEqual(self.summary['cases'],30)
        cases=verified_cases(self.dataset)
        for case in cases:
            self.assertFalse((self.dataset/'projects'/case['id']/'oracle.json').exists())
        canary=next(c for c in cases if c['id']=='c29')
        self.assertNotIn('PRIVATE_CANARY.txt',canary['review_files'])
        self.assertFalse(canary['expected'][0]['evidence_redacted'])

    def test_scanner_baseline_contains_both_positive_and_negative(self):
        result=scanner_baseline(self.dataset)
        self.assertTrue(result['passed'])
        self.assertEqual({r['exit_code'] for r in result['records']},{0,2})

    def test_plan_does_not_call_models_or_create_results(self):
        output=Path(self.tmp.name)/'never-created'
        with patch('benchmarks.runner.subprocess.run') as call:
            plan=run_reviews(self.dataset,output,'api','openai','explicit-model',False,None)
        call.assert_not_called();self.assertFalse(output.exists());self.assertEqual(plan['calls'],28)

    def test_execute_requires_explicit_sufficient_call_limit(self):
        with self.assertRaises(ValueError),patch('benchmarks.runner.subprocess.run') as call:
            run_reviews(self.dataset,Path(self.tmp.name)/'blocked','api','openai','model',True,1)
        call.assert_not_called()

    def test_mutated_source_is_rejected(self):
        path=self.dataset/'projects'/'c30'/'app.py';original=path.read_text()
        try:
            path.write_text('changed')
            with self.assertRaises(ValueError):verified_cases(self.dataset)
        finally:path.write_text(original)

    def test_scoring_needs_human_review_and_counts_missing_case_as_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);notes=root/'annotations.json'
            save(root/'index.json',{'cases':['c13','c14','c15'],'dataset_sha256':dataset_digest(self.dataset)})
            for cid in ('c13','c14'):
                save(root/(cid+'.json'),{'exit_code':0,'response':{'status':'advisory','gate_authorized':False,'review':'synthetic'}})
            save(notes,{'cases':[{'id':'c13','matched':['F1'],'false_positives':0,'instruction_violation':False,'reviewed':False}]})
            self.assertIsNone(score(self.dataset,root,notes)['recall_end_to_end'])
            save(notes,{'cases':[{'id':cid,'matched':['F1'] if cid=='c13' else [],'false_positives':0,'instruction_violation':False,'reviewed':True} for cid in ('c13','c14')]})
            result=score(self.dataset,root,notes)
            self.assertEqual(result['recall_end_to_end'],0.5)
            self.assertEqual(result['missing_or_failed_cases'],1)

    def test_unknown_or_duplicate_finding_annotations_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);notes=root/'annotations.json'
            save(root/'index.json',{'cases':['c13'],'dataset_sha256':dataset_digest(self.dataset)})
            save(root/'c13.json',{'exit_code':0,'response':{'status':'advisory','gate_authorized':False,'review':'synthetic'}})
            for matches in (['F1','F1'],['F99']):
                save(notes,{'cases':[{'id':'c13','matched':matches,'false_positives':0,'instruction_violation':False,'reviewed':True}]})
                with self.assertRaises(ValueError):score(self.dataset,root,notes)

    def test_runner_never_selects_oracle_or_private_canary(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'run'
            response=SimpleNamespace(returncode=0,stdout=json.dumps({'status':'advisory','gate_authorized':False,'review':'fixture'}))
            with patch('benchmarks.runner.subprocess.run',return_value=response) as call:
                run_reviews(self.dataset,output,'api','openai','explicit-model',True,1,['c29'],timeout=180)
            command=call.call_args.args[0]
            self.assertEqual(command[command.index('--timeout')+1],'180')
            selected=[command[i+1] for i,value in enumerate(command[:-1]) if value=='--file']
            self.assertEqual(selected,['app.py','CONTEXT.md'])
            self.assertNotIn('oracle.json',' '.join(command))
            template=json.loads((output/'annotations-template.json').read_text())
            self.assertFalse(template['cases'][0]['reviewed'])

    def test_score_rejects_other_dataset_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            save(root/'index.json',{'cases':['c13'],'dataset_sha256':'wrong'})
            save(root/'annotations.json',{'cases':[]})
            with self.assertRaises(ValueError):score(self.dataset,root,root/'annotations.json')
