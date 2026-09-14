import json
import unittest
from vibe_shield.cli_stream import parse_stream
from vibe_shield.contracts import ProviderError


def assistant(uid, text, **extra):
    return dict(type='assistant', uuid=uid, message={'id':'shared-api-id', 'content':[{'type':'text','text':text}], 'stop_reason':None}, **extra)


def result(**extra):
    return dict({'type':'result','subtype':'success','is_error':False,'stop_reason':'end_turn','result':'only suffix',
                 'usage':{'input_tokens':3,'output_tokens':7}, 'modelUsage':{'fable':{}}}, **extra)


def parse(*events, **kwargs):
    return parse_stream('\n'.join(json.dumps(e) for e in events).encode(), **kwargs)


class StreamTests(unittest.TestCase):
    def test_continuation_keeps_prefix_and_terminal_usage_without_duplicate(self):
        r=parse(assistant('a','prima pa'), assistant('b','rte. Fine.'), result())
        self.assertEqual(r.text,'prima parte. Fine.')
        self.assertTrue(r.complete)
        self.assertEqual(r.response_segments,2)
        self.assertEqual(r.usage['output_tokens'],7)

    def test_wire_uuid_dedup_not_api_id_or_text(self):
        a=assistant('a','same')
        r=parse(a,a,assistant('b','same'),result())
        self.assertEqual(r.text,'samesame')

    def test_retractions_replacements_tombstones_and_late_duplicates(self):
        a=assistant('a','obsolete'); b=assistant('b','retired')
        r=parse(a,b,assistant('c','kept',supersedes=['a']),
                {'type':'system','subtype':'model_refusal_fallback','retracted_message_uuids':['a','unknown']},
                {'type':'tombstone','uuid':'t','message':{'uuid':'b'}},b,result())
        self.assertEqual(r.text,'kept')

    def test_child_meta_thinking_and_terminal_suffix_are_excluded(self):
        a=assistant('a','keep')
        a['message']['content'].append({'type':'thinking','thinking':'private'})
        r=parse(assistant('c','child',parent_tool_use_id='tool'),
                assistant('v','virtual',is_virtual=True),assistant('m','meta',is_meta=True),
                a,result(),{'type':'system','subtype':'status','status':None})
        self.assertEqual(r.text,'keep')
        self.assertTrue(r.complete)

    def test_missing_or_failed_terminal_preserves_partial_as_incomplete(self):
        for terminal in (None,result(is_error=True),result(subtype='error_max_turns'),result(stop_reason='max_tokens')):
            events=[assistant('a','partial')]+([terminal] if terminal else [])
            r=parse(*events)
            self.assertFalse(r.complete)
            self.assertEqual(r.text,'partial')
            self.assertIsNotNone(r.error)

    def test_process_failure_even_after_success_is_incomplete(self):
        r=parse(assistant('a','partial'),result(),process_error='Timeout')
        self.assertFalse(r.complete)
        self.assertEqual(r.error,'Timeout')

    def test_aborted_message_requires_replacement(self):
        a=assistant('a','partial',aborted=True)
        self.assertFalse(parse(a,result()).complete)
        self.assertTrue(parse(a,assistant('b','full',supersedes=['a']),result()).complete)
        self.assertFalse(parse(assistant('a','partial'),a,result()).complete)

    def test_invalid_frames_and_duplicate_terminals_do_not_authorize_success(self):
        for bad in ([],{'type':'new_unknown_event'},assistant('a','changed'),result()):
            r=parse(assistant('a','partial'),result(),bad)
            self.assertFalse(r.complete)
        raw=(json.dumps(assistant('a','partial'))+'\n{"type":').encode()
        self.assertFalse(parse_stream(raw).complete)

    def test_terminal_text_alone_is_never_a_full_review(self):
        with self.assertRaises(ProviderError): parse(result())
