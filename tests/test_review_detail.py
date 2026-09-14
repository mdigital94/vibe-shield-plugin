import unittest
from vibe_shield.review import prompt_for

class DetailTests(unittest.TestCase):
    def test_concise_keeps_source_and_boundaries_but_omits_transport_metadata(self):
        f={'path':'app.py','content':'print(1)','sha256':'hash-only','bytes':8}
        compact=prompt_for([f]); full=prompt_for([f],'detailed')
        self.assertIn('print(1)',compact)
        self.assertIn('UNTRUSTED_SOURCE_JSON',compact)
        self.assertNotIn('hash-only',compact)
        self.assertIn('hash-only',full)
        self.assertIn('RISULTATI',compact)
        self.assertIn('LIMITI',compact)
        with self.assertRaises(ValueError):prompt_for([f],'unknown')
