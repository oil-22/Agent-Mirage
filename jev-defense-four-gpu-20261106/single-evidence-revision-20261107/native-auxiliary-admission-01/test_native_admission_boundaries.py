"""Pure CPU boundary fixtures: no real processor, tensor/model loading or CUDA."""
import ast,copy,hashlib,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import native_image_admission as worker

HERE=Path(__file__).resolve().parent
ROOT=None
CONTRACT_PATH=HERE.parent/'evidence-contract/image_evidence.py'


def minimal_manifest(output):
    return {'schema_version':'native-image-admission-v1','attempt_id':'scripted-fixture',
        'mode':'cpu_admission_only','output_root':str(output),'cpu_admission_authorized':True,
        'gpu_inference_authorized':False,
        'base_model':{'repo':worker.BASE_REPO,'revision':worker.BASE_REVISION,'local_path':worker.MODEL_PATH},
        'jev_relationship':{'repo':worker.JEV_REPO,'revision':worker.JEV_REVISION,
            'stage':'S2-shared-original-base','decision_adapter_loaded':False},
        'evidence_contract':{'source_path':str(CONTRACT_PATH),'sha256':worker.CONTRACT_SHA256},
        'metadata_files':[{'filename':name,'bytes':1,'sha256':'0'*64}for name in sorted(worker.REQUIRED_METADATA)],
        'prior_weight_identity':{'receipt_path':'unused-fixture.json','receipt_sha256':'0'*64},
        'weight_file_stats':[{'filename':'model-00001.safetensors','bytes':4,'mtime_ns':1}],
        'requests':[{'request_id':'r0','path':'unused-fixture.json','sha256':'0'*64}],
        'expected_request_count':1,
        'native_input_policy':{'enable_thinking':False,'truncate':False,'image_count':1,
            'processor_overrides':{},'task_history_candidate_supplied':False},
        'future_aux_generation':{'max_new_tokens':2048,'do_sample':False,'temperature':1.0,
            'top_p':1.0,'top_k':0,'dtype':'bfloat16','attention_backend':'sdpa',
            'model_class':worker.MODEL_CLASS,'eos_stop_rule_status':'UNDECIDED_before_GPU_inference',
            'inference_performed_in_this_mode':False}}


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/('t'+self._testMethodName.split('_')[1]);self.root.mkdir()
        self.manifest=minimal_manifest(self.root/'out')

    def config_fixture(self):
        model=self.root/'fake-model';model.mkdir()
        config={'architectures':[worker.MODEL_CLASS],'model_type':'qwen3_5',
            'text_config':{'num_hidden_layers':32,'num_attention_heads':16,
                'max_position_embeddings':262144,'eos_token_id':248044}}
        for name in worker.REQUIRED_METADATA:
            value=config if name=='config.json'else({'weight_map':{'fixture.weight':'model-00001.safetensors'}}
                if name=='model.safetensors.index.json'else{})
            (model/name).write_bytes(worker.canonical(value))
        # Four fixture bytes are never a model or tensor checkpoint; only stat is used.
        shard=model/'model-00001.safetensors';shard.write_bytes(b'TEST')
        old=self.root/'old-identity-fixture.json';old.write_bytes(b'{"fixture":true}\n')
        self.manifest['metadata_files']=[{'filename':name,'bytes':(model/name).stat().st_size,
            'sha256':worker.digest((model/name).read_bytes())}for name in sorted(worker.REQUIRED_METADATA)]
        self.manifest['prior_weight_identity']={'receipt_path':str(old),'receipt_sha256':worker.digest(old.read_bytes())}
        stat=shard.stat();self.manifest['weight_file_stats']=[{'filename':shard.name,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}]
        out=self.root/'gate';out.mkdir()
        return model,out,worker.Journal(out)

    def request_fixture(self):
        from PIL import Image
        raw=io.BytesIO();Image.new('RGB',(20,12),'blue').save(raw,format='PNG')
        contract=worker.contract_from_pinned_source(CONTRACT_PATH)
        return contract,contract.build_image_only_request(raw.getvalue(),worker.BASE_REPO,worker.BASE_REVISION),raw.getvalue()

    def bind(self,request):
        path=self.root/'request.json';raw=worker.canonical(request);path.write_bytes(raw)
        out=self.root/'request-output';out.mkdir()
        return {'request_id':'r0','path':str(path),'sha256':worker.digest(raw)},out

    def test_01_valid_frozen_manifest_only(self):
        self.assertIs(worker.validate_manifest(self.manifest),self.manifest)

    def test_02_wrong_pins_and_false_adapter_claim_rejected(self):
        for mutate in [lambda x:x['base_model'].update(revision='0'*40),
                       lambda x:x['jev_relationship'].update(revision='1'*40),
                       lambda x:x['jev_relationship'].update(decision_adapter_loaded=True)]:
            value=copy.deepcopy(self.manifest);mutate(value)
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)

    def test_03_gpu_cpu_inference_and_unapproved_modes_rejected(self):
        for key,value in [('mode','gpu'),('cpu_admission_authorized',False),('gpu_inference_authorized',True)]:
            manifest=copy.deepcopy(self.manifest);manifest[key]=value
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(manifest)

    def test_04_context_multimage_and_overrides_rejected(self):
        for change in [{'image_count':2},{'task_history_candidate_supplied':True},
                       {'truncate':True},{'processor_overrides':{'max_pixels':256}},
                       {'enable_thinking':True}]:
            value=copy.deepcopy(self.manifest);value['native_input_policy'].update(change)
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)
        value=copy.deepcopy(self.manifest);value['task']='SECRET_TARGET'
        with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)

    def test_05_malicious_metadata_paths_and_duplicates_rejected(self):
        for name in ['../config.json','model.safetensors','unexpected-defaults.json']:
            value=copy.deepcopy(self.manifest);value['metadata_files'][0]['filename']=name
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)
        value=copy.deepcopy(self.manifest);value['metadata_files'].append(copy.deepcopy(value['metadata_files'][0]))
        with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)

    def test_06_request_inventory_count_duplicate_and_path_ids_rejected(self):
        for mutate in [lambda x:x.update(expected_request_count=2),
                       lambda x:x['requests'][0].update(request_id='../r0'),
                       lambda x:(x['requests'].append(copy.deepcopy(x['requests'][0])),x.update(expected_request_count=2))]:
            value=copy.deepcopy(self.manifest);mutate(value)
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)

    def test_07_eos_old_override_and_output_budget_change_rejected(self):
        for change in [{'max_new_tokens':4096},{'do_sample':True},{'eos_token_id':[248044,248046]},
                       {'eos_stop_rule_status':'ALREADY_FROZEN'}]:
            value=copy.deepcopy(self.manifest);value['future_aux_generation'].update(change)
            with self.assertRaises(worker.AdmissionError):worker.validate_manifest(value)

    def test_08_pure_metadata_gate_old_sha_link_is_not_stat_continuity(self):
        model,out,journal=self.config_fixture()
        with patch.object(worker,'MODEL_PATH',str(model)):
            worker.metadata_gate(self.manifest,out,journal)
        row=json.loads((out/'metadata-gate.json').read_text())
        self.assertFalse(row['weight_bytes_opened_or_rehashed'])
        self.assertFalse(row['stat_continuity_since_old_fullhash_established'])
        self.assertFalse(row['current_GPU_tensors_verified'])

    def test_09_unbound_optional_processor_metadata_rejected(self):
        model,out,journal=self.config_fixture();(model/'processor_config.json').write_text('{}')
        with patch.object(worker,'MODEL_PATH',str(model)),self.assertRaisesRegex(worker.AdmissionError,'unbound optional'):
            worker.metadata_gate(self.manifest,out,journal)

    def test_10_unofficial_extra_generation_config_rejected(self):
        model,out,journal=self.config_fixture();(model/'generation_config.json').write_text('{}')
        with patch.object(worker,'MODEL_PATH',str(model)),self.assertRaisesRegex(worker.AdmissionError,'has no generation_config'):
            worker.metadata_gate(self.manifest,out,journal)

    def test_11_changed_metadata_or_current_stat_rejected(self):
        model,out,journal=self.config_fixture();(model/'chat_template.jinja').write_text('changed')
        with patch.object(worker,'MODEL_PATH',str(model)),self.assertRaisesRegex(worker.AdmissionError,'identity mismatch'):
            worker.metadata_gate(self.manifest,out,journal)

    def test_12_current_shard_stat_mismatch_rejected(self):
        model,out,journal=self.config_fixture();self.manifest['weight_file_stats'][0]['mtime_ns']-=1
        with patch.object(worker,'MODEL_PATH',str(model)),self.assertRaisesRegex(worker.AdmissionError,'NEW frozen manifest'):
            worker.metadata_gate(self.manifest,out,journal)

    def test_13_single_original_request_passes_no_extra_context(self):
        contract,request,image=self.request_fixture();binding,out=self.bind(request)
        actual,raw=worker.bound_request(binding,out,contract)
        self.assertEqual(actual,request);self.assertEqual(raw,image)
        self.assertEqual((out/'received-original.image').read_bytes(),image)

    def test_14_extra_task_or_multi_image_request_rejected(self):
        contract,request,_=self.request_fixture()
        for index,change in enumerate([{'task':'SECRET_TARGET'},{'history':[]},{'candidate':'CLICK'},
                       {'images':[request['image_base64'],request['image_base64']]}]):
            value=copy.deepcopy(request);value.update(change)
            sub=self.root/('case'+str(index));sub.mkdir()
            path=sub/'request.json';raw=worker.canonical(value);path.write_bytes(raw)
            with self.assertRaises(contract.EvidenceContractError):
                worker.bound_request({'path':str(path),'sha256':worker.digest(raw)},sub,contract)

    def test_15_changed_prompt_or_request_sha_rejected(self):
        contract,request,_=self.request_fixture();request['prompt']+=' Solve the target task.'
        binding,out=self.bind(request)
        with self.assertRaises(contract.EvidenceContractError):worker.bound_request(binding,out,contract)

    def test_16_partial_terminal_keeps_completed_count_and_duplicate_root_immutable(self):
        path=self.root/'manifest.json';path.write_bytes(worker.canonical(self.manifest));out=Path(self.manifest['output_root'])
        def fake_cpu(manifest,root,journal,config,rows):
            rows.append({'fixture_admitted':True});journal.append('fixture_partial_admitted',rows[-1])
            raise worker.AdmissionError('scripted partial failure')
        argv=['native_image_admission.py','--mode','cpu-admission','--manifest',str(path),'--output',str(out)]
        with patch.object(sys,'argv',argv),patch.object(worker,'metadata_gate',return_value={}),patch.object(worker,'cpu_admit',side_effect=fake_cpu):
            self.assertEqual(worker.main(),1)
            terminal=json.loads((out/'terminal.json').read_text());self.assertEqual(terminal['admitted_requests'],1)
            self.assertEqual(terminal['model_calls'],0);self.assertEqual(terminal['status'],'failed')
            seal=(out/'seal.json').read_bytes()
            with self.assertRaises(FileExistsError):worker.main()
            self.assertEqual((out/'seal.json').read_bytes(),seal)

    def test_17_bad_manifest_claimed_and_preserved_without_processor(self):
        value=copy.deepcopy(self.manifest);value['task']='SECRET_TARGET'
        path=self.root/'manifest.json';path.write_bytes(worker.canonical(value));out=Path(value['output_root'])
        argv=['native_image_admission.py','--mode','cpu-admission','--manifest',str(path),'--output',str(out)]
        with patch.object(sys,'argv',argv),patch.object(worker,'cpu_admit',side_effect=AssertionError('processor path reached')):
            self.assertEqual(worker.main(),1)
        self.assertTrue((out/'seal.json').is_file())
        self.assertEqual((out/'input-manifest.original.json').read_bytes(),path.read_bytes())
        self.assertEqual(json.loads((out/'terminal.json').read_text())['admitted_requests'],0)

    def test_18_AST_has_no_model_loading_generate_or_CUDA_calls(self):
        tree=ast.parse((HERE/'native_image_admission.py').read_text(encoding='utf8'))
        calls=[node for node in ast.walk(tree)if isinstance(node,ast.Call)]
        self.assertFalse(any(isinstance(node.func,ast.Attribute)and node.func.attr in {'generate','cuda'}for node in calls))
        pretrained=[ast.unparse(node.func.value)for node in calls
            if isinstance(node.func,ast.Attribute)and node.func.attr=='from_pretrained']
        self.assertEqual(sorted(pretrained),['AutoConfig','AutoProcessor'])
        self.assertTrue(any(isinstance(node.func,ast.Attribute)and node.func.attr=='from_model_config'for node in calls))
        self.assertNotIn('torch',sys.modules)


def run():
    global ROOT
    ROOT=HERE/sys.argv[1];ROOT.mkdir(exist_ok=False)
    snapshot=ROOT/'source';snapshot.mkdir()
    for path in [HERE/'native_image_admission.py',Path(__file__),HERE/'README.md',CONTRACT_PATH]:
        (snapshot/path.name).write_bytes(path.read_bytes())
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Boundaries))
    (ROOT/'tests.log').write_text(log.getvalue(),encoding='utf8')
    receipt={'tests':result.testsRun,'success':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
        'real_native_processor_calls':0,'model_calls':0,'GPU_calls':0,
        'fixture_only_metadata_and_terminal_simulation':True,'launch_ready':False}
    (ROOT/'receipt.json').write_bytes(worker.canonical(receipt)+b'\n')
    files=[{'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':worker.digest(path.read_bytes())}
        for path in sorted(ROOT.rglob('*'))if path.is_file()]
    (ROOT/'seal.json').write_bytes(worker.canonical({'files':files})+b'\n')
    print(json.dumps(receipt))
    if not result.wasSuccessful():print(log.getvalue());raise SystemExit(1)


if __name__=='__main__':run()
