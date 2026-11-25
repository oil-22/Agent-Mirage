import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import background_start as b


class BackgroundGate(unittest.TestCase):
    def setUp(self):
        native=patch.object(b,'BASE',b.BASE.resolve());native.start();self.addCleanup(native.stop)
        self.args=SimpleNamespace(spec=b.BASE/'gui-final-readiness-01/launch-spec.json',spec_sha256='a'*64)
        self.spec={'batch_root':str(b.BASE/'gui-batch-image-observer-01'),
            'linked_root':str(b.BASE/'gui-final-readiness-01'),
            'wrapper_source_sha256':'a2bc6313b807cd800d245428d77f50dd7449e970e2201c2d1a926dd7b230429f',
            'ownership_evidence':{'path':'owner','sha256':'b'*64}}
    def call(self,uid=1015):
        with patch.object(b.os,'getuid',return_value=uid,create=True),patch.object(b.g,'bound',side_effect=[self.spec,{}]),\
                patch.object(b.g,'ownership'),patch.object(b.g,'sha',return_value=self.spec['wrapper_source_sha256']):
            return b.validate(self.args)
    def test_valid_no_process_spawn(self):self.assertEqual(self.call()[0],self.spec)
    def test_wrong_uid(self):
        with self.assertRaises(RuntimeError):self.call(1006)
    def test_wrong_spec_path(self):
        self.args.spec=b.BASE/'old/launch-spec.json'
        with self.assertRaises(RuntimeError):self.call()
    def test_old_batch(self):
        self.spec['batch_root']=str(b.BASE/'oldbatch')
        with self.assertRaises(RuntimeError):self.call()
    def test_changed_wrapper(self):
        self.spec['wrapper_source_sha256']='0'*64
        with self.assertRaises(RuntimeError):self.call()
    def test_wrong_linked_gate(self):
        self.spec['linked_root']=str(b.BASE/'oldgate')
        with self.assertRaises(RuntimeError):self.call()


if __name__=='__main__':unittest.main()
