"""CPU-only adversarial admission checks; no torch/model/GPU import or call."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import native_image_gpu_preflight as worker

def sha(raw):return hashlib.sha256(raw).hexdigest()

class Boundaries(unittest.TestCase):
    def manifest(self):
        value={k:None for k in ['schema_version','attempt_id','output_root','gpu_authorized','cpu_proof',
            'source_labels','input_package','base_model','jev_relationship','lease_path','expected_holder',
            'resource_gate','evidence_contract','prior_weight_identity','official_base_api','metadata_files','weight_files',
            'requests','generation','limits']}
        value.update(schema_version='single-image-GPU-preflight-v1',gpu_authorized=True,
            base_model={'repo':worker.BASE_REPO,'revision':worker.BASE_REVISION,'local_path':worker.MODEL_PATH},
            jev_relationship={'repo':'autotrust/JEV-9B','revision':worker.JEV_REVISION,
                'stage':'S2-shared-original-base','decision_adapter_loaded':False},
            generation={'max_new_tokens':2048,'do_sample':False,'temperature':1.0,'top_p':1.0,'top_k':0,
                'num_beams':1,'num_return_sequences':1,'eos_token_id':[248044,248046],
                'enable_thinking':False,'seed':0,'dtype':'bfloat16','attention_backend':'sdpa'},
            limits={'requests':4,'automatic_format_retries':0,'semantic_resampling':False,
                'primary_model_calls':0,'GUI_actions':0,'scorer':0,'paid_API':0},
            requests=[{'request_id':name,'image_sha256':str(i)*64}for i,name in enumerate(['S01','S07','S13','S25'])])
        return value

    def test_budget_and_model_separation(self):
        base=self.manifest();worker.validate_manifest(base)
        variants=[]
        for field,val in [('automatic_format_retries',1),('primary_model_calls',1),('GUI_actions',1),
                          ('semantic_resampling',True),('requests',5)]:
            m=copy.deepcopy(base);m['limits'][field]=val;variants.append(m)
        for field,val in [('max_new_tokens',4096),('num_return_sequences',2),('enable_thinking',True),
                          ('eos_token_id',[248044]),('dtype','float16')]:
            m=copy.deepcopy(base);m['generation'][field]=val;variants.append(m)
        m=copy.deepcopy(base);m['jev_relationship']['decision_adapter_loaded']=True;variants.append(m)
        m=copy.deepcopy(base);m['task']='hidden task';variants.append(m)
        m=copy.deepcopy(base);m['requests'][1]['image_sha256']=m['requests'][0]['image_sha256'];variants.append(m)
        for i,m in enumerate(variants):
            with self.subTest(i=i),self.assertRaises(ValueError):worker.validate_manifest(m)

    def test_full_weight_integrity_gate_and_corruption(self):
        with tempfile.TemporaryDirectory(prefix='jev-wt-')as temp:
            root=Path(temp);model=root/'model';model.mkdir();out=root/'out';out.mkdir()
            data=b'original complete shard bytes'
            (model/'test.safetensors').write_bytes(data)
            index=json.dumps({'weight_map':{'weight':'test.safetensors'}}).encode()
            (model/'model.safetensors.index.json').write_bytes(index)
            prior={'files':{'Qwen3.5-9B/test.safetensors':{'bytes':len(data),'sha256':sha(data)}}}
            original=root/'prior.json';original.write_text(json.dumps(prior),encoding='utf-8')
            official=root/'official.json';official.write_text(json.dumps({'id':worker.BASE_REPO,
                'sha':worker.BASE_REVISION,'siblings':[{'rfilename':'test.safetensors',
                    'lfs':{'sha256':sha(data),'size':len(data)}}]}),encoding='utf-8')
            manifest={'prior_weight_identity':{'path':str(original),'sha256':worker.sha(original)},
                'official_base_api':{'path':str(official),'sha256':worker.sha(official)},
                'metadata_files':[{'filename':'model.safetensors.index.json','bytes':len(index),'sha256':sha(index)}],
                'weight_files':[{'filename':'test.safetensors','bytes':len(data),'sha256':sha(data)}]}
            with patch.object(worker,'MODEL_PATH',str(model)):
                result=worker.current_weight_identity(manifest,out,worker.Journal(out))
                self.assertEqual(result[0]['current_sha256'],sha(data))
                (model/'generation_config.json').write_bytes(b'{}')
                extra=root/'extra';extra.mkdir()
                with self.assertRaisesRegex(ValueError,'Native model file set changed'):
                    worker.current_weight_identity(manifest,extra,worker.Journal(extra))
                (model/'generation_config.json').unlink()
                (model/'test.safetensors').write_bytes(b'X'+data[1:])
                out2=root/'corrupt';out2.mkdir()
                with self.assertRaisesRegex(ValueError,'Current full shard identity mismatch'):
                    worker.current_weight_identity(manifest,out2,worker.Journal(out2))
            self.assertFalse((out2/'current-weight-identity.json').exists())

    def test_sealed_CPU_proof_mutation(self):
        with tempfile.TemporaryDirectory(prefix='jev-proof-')as temp:
            root=Path(temp);(root/'input_ids.tensor').write_bytes(b'complete IDs')
            seal={'files':[{'path':'input_ids.tensor','sha256':worker.sha(root/'input_ids.tensor')}]}
            (root/'seal.json').write_text(json.dumps(seal),encoding='utf-8')
            expected=worker.sha(root/'seal.json');worker.verify_seal(root,expected)
            (root/'input_ids.tensor').write_bytes(b'other IDs')
            with self.assertRaisesRegex(ValueError,'Sealed artifact changed'):worker.verify_seal(root,expected)

    def test_immutable_write_and_journal_chain(self):
        with tempfile.TemporaryDirectory(prefix='jev-chain-')as temp:
            root=Path(temp);journal=worker.Journal(root)
            journal.append('request',{'raw':'original'});journal.append('failure',{'not_retried':True})
            previous='0'*64
            for event in map(json.loads,(root/'journal.jsonl').read_bytes().splitlines()):
                self.assertEqual(event['previous'],previous)
                actual=event.pop('sha256');self.assertEqual(actual,worker.digest(worker.canonical(event)))
                previous=actual
            worker.write(root/'receipt.json',{'terminal':True})
            with self.assertRaises(FileExistsError):worker.write(root/'receipt.json',{'terminal':False})

if __name__=='__main__':unittest.main(verbosity=2)
