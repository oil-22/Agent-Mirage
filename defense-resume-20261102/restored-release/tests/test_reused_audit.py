import json,tempfile,unittest
from pathlib import Path
from audit_vwa_v2 import audit
from defense.core import digest

class ReusedAuditTests(unittest.TestCase):
    def fixture(self,root):
        old=root/'old';old.mkdir();raw=json.dumps({'run':{'arm':'baseline'},'outcome':'model_stop','official_reward':1,'scoring_status':'complete'}).encode()
        (old/'complete.json').write_bytes(raw)
        batch=root/'new';run=batch/'runs'/'same-task';run.mkdir(parents=True)
        marker=run/'complete.json';marker.write_text(json.dumps({'attempt':str(old),'sha256':digest(raw)}))
        return batch,old,marker
    def test_reused_completed_baseline_is_counted_and_explicitly_marked(self):
        with tempfile.TemporaryDirectory()as t:
            batch,_,_=self.fixture(Path(t));result=audit(batch)
            self.assertEqual(result['completed'],1)
            self.assertTrue(result['rows'][0]['reused_from_prior_batch'])
    def test_changed_source_cannot_be_silently_reused(self):
        with tempfile.TemporaryDirectory()as t:
            batch,old,_=self.fixture(Path(t));(old/'complete.json').write_text('{}')
            with self.assertRaises(AssertionError):audit(batch)

if __name__=='__main__':unittest.main()
