import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import capacity_gate as gate
import four_gpu_contract as contract
import marker_stop_helpers as stops
import submit_capacity_once as submit
import run_one_frozen_judge as client
import preflight_service as worker
import os

HERE=Path(__file__).resolve().parent
PARENT=None
WIRE=None


def normalized(path):return ast.parse(path.read_text(encoding='utf8'))
def dump(tree):return ast.dump(tree,include_attributes=False)


class Sources(unittest.TestCase):
    def test_worker_only_atomic_save_import_and_runtime_label_changed(self):
        before=normalized(PARENT/'preflight_service.py');after=normalized(HERE/'preflight_service.py')
        class Label(ast.NodeTransformer):
            def visit_Constant(self,node):
                if node.value=='explicit_asymmetric_14_22_22_6':node.value='explicit_asymmetric_18_20_20_6'
                return node
        def retained(tree):
            tree.body=[row for row in tree.body if not(isinstance(row,ast.FunctionDef)and row.name=='save')
                and not(isinstance(row,ast.Import)and any(alias.name=='uuid'for alias in row.names))]
            return tree
        self.assertEqual(dump(retained(before)),dump(retained(Label().visit(after))))

    def test_contract_only_device_map_changed(self):
        before=normalized(PARENT/'four_gpu_contract.py');after=normalized(HERE/'four_gpu_contract.py')
        before.body=[row for row in before.body if not(isinstance(row,ast.FunctionDef)and row.name=='primary_device_map')]
        after.body=[row for row in after.body if not(isinstance(row,ast.FunctionDef)and row.name=='primary_device_map')]
        self.assertEqual(dump(before),dump(after))

    def test_exact_64_layer_partition(self):
        mapping=contract.primary_device_map();counts=[0]*4
        for layer in range(64):counts[mapping['model.language_model.layers.'+str(layer)]]+=1
        self.assertEqual(counts,[14,22,22,6]);self.assertEqual(mapping['model.visual'],0)
        self.assertEqual(mapping['lm_head'],3)

    def test_frozen_failed_wire_bound(self):
        raw=WIRE.read_bytes();body=json.loads(raw);fingerprint=contract.request_fingerprint(body)
        admission={'mode':'capacity_preflight','max_new_calls':1,'GUI_actions':0,
            'requests':[{'fingerprint':fingerprint,'wire_sha256':hashlib.sha256(raw).hexdigest()}]}
        allowed=contract.validate_admission(admission)
        self.assertEqual(contract.validate_frozen_wire(raw,body,allowed),fingerprint)
        with self.assertRaises(ValueError):contract.validate_frozen_wire(raw+b' ',body,allowed)

    def test_helper_cannot_admit_one_call(self):
        with self.assertRaises(ValueError):contract.validate_admission({'mode':'resident_only',
            'max_new_calls':1,'GUI_actions':0,'requests':[]})

    def test_manifest_path_escape(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);manifest=root/'manifest.json';manifest.write_text(json.dumps({'../outside':'0'*64}))
            with self.assertRaises(AssertionError):gate.verify_manifest(root,manifest,gate.sha(manifest))

    def test_manifest_detects_changed_file(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);data=root/'data';data.write_bytes(b'original')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'data':gate.sha(data)}))
            gate.verify_manifest(root,manifest,gate.sha(manifest));data.write_bytes(b'changed')
            with self.assertRaises(AssertionError):gate.verify_manifest(root,manifest,gate.sha(manifest))

    def test_manifest_detects_unsealed_extra(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);data=root/'data';data.write_bytes(b'original')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'data':gate.sha(data)}))
            (root/'extra').write_bytes(b'late')
            with self.assertRaises(AssertionError):gate.verify_manifest(root,manifest,gate.sha(manifest))


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.expected={'pid':123,'uid':1033,'start_ticks':'456','command':'exact command'}
        self.child={'identity':self.expected,'process':Mock(pid=123)}

    def test_reaped_child_never_read_or_signal(self):
        self.child['process'].poll.return_value=0
        with patch.object(stops,'identity')as identify:
            self.assertIsNone(stops.lifecycle_identity(self.child));identify.assert_not_called()

    def test_running_exact_identity_retained(self):
        self.child['process'].poll.return_value=None
        with patch.object(stops,'identity',return_value=self.expected):
            self.assertEqual(stops.lifecycle_identity(self.child),self.expected)

    def test_teardown_reaped_during_identity_check(self):
        self.child['process'].poll.side_effect=[None,0]
        actual={**self.expected,'command':''}
        with patch.object(stops,'identity',return_value=actual):
            self.assertIsNone(stops.lifecycle_identity(self.child))
            self.assertNotIn('zombie_observed',self.child)

    def test_matching_zombie_is_not_signalled_or_exit_normalized(self):
        self.child['process'].poll.return_value=None
        actual={**self.expected,'command':''}
        fake_path=Mock();fake_path.read_text.return_value='123 (python) Z 1 2 3'
        with patch.object(stops,'identity',return_value=actual),patch.object(stops,'Path',return_value=fake_path):
            self.assertIsNone(stops.lifecycle_identity(self.child))
        self.assertTrue(self.child['zombie_observed']['exit_code_not_inferred'])
        self.assertTrue(self.child['zombie_observed']['no_signal_sent'])

    def test_live_reused_or_changed_identity_rejected(self):
        self.child['process'].poll.return_value=None
        actual={**self.expected,'command':'foreign command','start_ticks':'999'}
        fake_path=Mock();fake_path.read_text.return_value='123 (python) S 1 2 3'
        with patch.object(stops,'identity',return_value=actual),patch.object(stops,'Path',return_value=fake_path):
            with self.assertRaises(RuntimeError):stops.lifecycle_identity(self.child)


class Publication(unittest.TestCase):
    def test_worker_atomic_evidence_complete_before_visible_and_nooverwrite(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);target=root/'seal.json';value={'request':'原始完整证据','calls':1}
            real_link=os.link
            def checked_link(source,destination):
                self.assertFalse(target.exists())
                self.assertNotEqual(Path(source).suffix,'.json')
                self.assertEqual(json.loads(Path(source).read_bytes()),value)
                real_link(source,destination)
            with patch.object(worker.os,'link',side_effect=checked_link):worker.save(target,value)
            self.assertEqual(json.loads(target.read_bytes()),value)
            with self.assertRaises(FileExistsError):worker.save(target,{'replacement':True})
            self.assertEqual(json.loads(target.read_bytes()),value)
            self.assertEqual(set(p.name for p in root.iterdir()),{'seal.json'})

    def test_actual_client_seal_excludes_itself_and_all_hashes_match(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'request-wire.json').write_bytes(b'{"original":"wire"}')
            (root/'response.raw').write_bytes(b'{"status":"ok"}')
            client.seal_client_root(root)
            manifest=json.loads((root/'seal.json').read_bytes())
            self.assertNotIn('seal.json',manifest)
            self.assertEqual(set(manifest),{'request-wire.json','response.raw'})
            for name,expected in manifest.items():self.assertEqual(gate.sha(root/name),expected)

    def test_target_appears_only_after_full_file(self):
        with tempfile.TemporaryDirectory()as temp:
            target=Path(temp)/'new-command.json';raw=b'{"complete":"new finite command"}'
            real_link=os.link
            def checked_link(source,destination):
                self.assertFalse(target.exists())
                self.assertEqual(Path(source).read_bytes(),raw)
                self.assertNotEqual(Path(source).suffix,'.json')
                real_link(source,destination)
            with patch.object(submit.os,'link',side_effect=checked_link):submit.publish_no_clobber(target,raw)
            self.assertEqual(target.read_bytes(),raw)
            self.assertEqual(list(Path(temp).glob('*.tmp')),[])

    def test_existing_command_never_overwritten(self):
        with tempfile.TemporaryDirectory()as temp:
            target=Path(temp)/'command.json';target.write_bytes(b'old immutable')
            with self.assertRaises(FileExistsError):submit.publish_no_clobber(target,b'new command')
            self.assertEqual(target.read_bytes(),b'old immutable')
            self.assertEqual(len(list(Path(temp).iterdir())),1)

    def test_publish_failure_preserves_external_claim(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);target=root/'command.json';claim=root/'submission.once-only.json'
            claim.write_bytes(b'claim is retained')
            with patch.object(submit.os,'link',side_effect=OSError('injected publish failure')):
                with self.assertRaises(OSError):submit.publish_no_clobber(target,b'fully prepared')
            self.assertEqual(claim.read_bytes(),b'claim is retained');self.assertFalse(target.exists())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parent-root',type=Path,required=True)
    parser.add_argument('--frozen-wire',type=Path,required=True);args,remaining=parser.parse_known_args()
    PARENT=args.parent_root;WIRE=args.frozen_wire
    unittest.main(argv=[__file__]+remaining)
