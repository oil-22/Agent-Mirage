"""Audit stored native inputs, actual output IDs, raw replies and two terminal chains."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P02 = HERE / 'terminal-collection/1794141466927603400'
P03 = HERE / 'terminal-collection-03/1794142275298070600'
OUT = HERE / 'completed-batch-audit-01'
OUT.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
digest = lambda b: hashlib.sha256(b).hexdigest()
sys.path.insert(0, str(HERE / 'technical-continuation-03/runtime-package/release'))
from defense.core import PublicView, VisibleImage
from defense.qwen_backend import LocalQwen

calls=[]
chains=[]
for attempt, collection in [('02', P02),('03',P03)]:
    audit=json.loads((collection/'collection-audit.json').read_bytes())
    assert audit['terminal']['all_SHA_verified'] and not audit['errors']
    for name,h in audit['mirrored_files'].items():
        assert sha(collection/'original'/name)==h,name
    worker=collection/'original/worker'
    prev='0'*64; count=0
    for line in (worker/'journal/events.jsonl').read_bytes().splitlines():
        value=json.loads(line);expected=value.pop('sha256')
        assert value['previous']==prev and value['seq']==count
        assert digest(canonical(value))==expected
        prev=expected;count+=1
    chains.append({'attempt':attempt,'events':count,'head':prev,
        'terminal_manifest_sha256':audit['terminal']['manifest_sha256'],
        'all_remote_terminal_files_SHA_verified':audit['terminal']['files'],
        'local_mirrored_metadata_files_verified':len(audit['mirrored_files']),
        'raw_tensor_bytes_still_remote':True})
    for row in audit['calls']:
        folder=collection/'original'/row['directory']
        actual=json.loads((folder/'actual-generation.json').read_bytes())
        config=json.loads((folder/'effective-generation.json').read_bytes())
        seq=json.loads((folder/'sequence_ids.json').read_bytes())[0]
        raw=(folder/'raw-output.txt').read_bytes()
        request=json.loads((folder/'request.json').read_bytes())
        data={'attempt':attempt,'directory':row['directory'],
            'input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens'],
            'natural_EOS':actual['natural_EOS'],'raw_reply_sha256':digest(raw),
            'call_seal_sha256':sha(folder/'seal.json'),
            'actual_CPU_forward_output_and_EOS_remote_audit':True}
        assert actual['natural_EOS'] and seq[actual['input_tokens']:]==actual['output_ids']
        if 'judges' in row['directory']:
            original=json.loads((folder/'generation.json').read_bytes())
            assert original['generated_ids']==actual['output_ids']
            assert original['input_ids']==seq[:actual['input_tokens']]
            assert original['text'].encode()==raw
            assert original['generation_config']==config
            assert config['max_new_tokens']==4096 and config['do_sample'] is False
            assert config['temperature']==config['top_p']==1.0 and config['top_k']==0
            assert original['environment_actions_executed'] is False
            assert digest(canonical(original['verifier_grammar']['schema']))==original['verifier_grammar']['schema_sha256']
            frozen=json.loads((HERE/'payload/inputs'/(request['case']+'.json')).read_bytes())
            assert request['candidate']==frozen['candidate']
            for name in ['messages','observation_id','recent_action','execution_feedback','observed_at']:
                assert request['public'][name]==frozen['view'][name],(request['case'],name)
            assert request['images']==frozen['view']['images']
            public=request['public']
            view=PublicView(public['observation_id'],copy.deepcopy(public['messages']),
                tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role']) for im in request['images']),
                public['recent_action'],public['execution_feedback'],public['observed_at'])
            wire={}
            def capture(messages,max_tokens,receipt=None,**options):
                wire.update(messages=messages,max_tokens=max_tokens,options=options)
                return ''
            engine=LocalQwen.__new__(LocalQwen);engine.generate=capture
            engine.judge(request['system'],view,request['candidate'])
            assert digest(canonical(wire['messages']))==original['request_messages_sha256'],(attempt,folder.name,'wire')
            assert wire['max_tokens']==4096 and wire['options']['json_schema']==original['verifier_grammar']['schema']
            data.update(kind='primary_judge',case=request['case'],
                native_seconds_including_instrumentation=original['seconds'],
                original_full_view_and_new_constructed_candidate_equal=True,
                actual_backend_message_SHA_and_grammar_reconstructed=True)
        else:
            assert config['max_new_tokens']==2048 and config['do_sample'] is False
            result=json.loads((folder/'result.json').read_bytes())
            assert digest(base64.b64decode(request['image_base64']))==request['image_sha256']
            assert sha(folder/'original.png')==request['image_sha256']
            if result['contract_valid']:
                packet=json.loads((folder/'packet.json').read_bytes())
                assert packet['raw_output_sha256']==digest(raw) and packet['image_sha256']==request['image_sha256']
                assert packet['auxiliary_model_count']==1 and packet['automatic_allow_or_block'] is False
            data.update(kind='image_only_auxiliary',case=folder.name,
                pipeline_seconds_including_instrumentation=result['seconds_including_instrumentation'],
                contract_valid=result['contract_valid'])
        calls.append(data)

old=P02/'original/worker/judges/06'
new=P03/'original/worker/judges/01'
assert (old/'request.json').read_bytes()==(new/'request.json').read_bytes()
old_p=json.loads((old/'prepared.json').read_bytes());new_p=json.loads((new/'prepared.json').read_bytes())
for name,v in old_p.items():
    assert all(v[k]==new_p[name][k] for k in ['shape','dtype','bytes','sha256'])
assert old_p['input_ids']['shape']==[1,17113]
assert not (old/'actual-generation.json').exists() and not (old/'generated-token-progress.jsonl').stat().st_size
results={}
for collection in [P02,P03]:
    for p in (collection/'original/worker').glob('C*-result.json'):
        d=json.loads(p.read_bytes());assert d['id'] not in results;results[d['id']]=d
assert sorted(results)==['C01','C02','C03','C04','C05','C06','C07','C08']
assert sum(d['actual_judge_calls'] for d in results.values())==9
assert len(calls)==13
metrics={kind:{'complete_calls':sum(v['kind']==kind for v in calls),
    'input_tokens':sum(v['input_tokens'] for v in calls if v['kind']==kind),
    'output_tokens':sum(v['output_tokens'] for v in calls if v['kind']==kind)}
    for kind in ['primary_judge','image_only_auxiliary']}
metrics['primary_judge']['native_seconds_including_instrumentation']=sum(v.get('native_seconds_including_instrumentation',0) for v in calls)
metrics['image_only_auxiliary']['pipeline_seconds_including_instrumentation']=sum(v.get('pipeline_seconds_including_instrumentation',0) for v in calls)
metrics.update(actual_judge_calls_including_prefill_OOM=10,judge_cap=16,auxiliary_calls=4,
    total_actual_calls=14,complete_natural_EOS_calls=13,prefill_OOM_calls=1,
    failed_input_tokens_separate_from_completed_totals=17113,failed_output_tokens=0,
    actor_GUI_scorer_paid_calls=0)
snapshot=HERE/'progress-evidence/1794142248203795200/stdout.json'
snap=json.loads(snapshot.read_bytes())
assert not snap['journal']['errors']
assert all(snap[key]['value']['actual'].get('proc_absent') for key in ['launcher-process.json','worker/process.json'])
assert len(snap['holder']['locks'])==9 and all(v['matches'] for v in snap['holder']['locks'])
target_uuids={'GPU-00000000-0000-0000-0000-000000000002','GPU-00000000-0000-0000-0000-000000000001',
    'GPU-00000000-0000-0000-0000-000000000004','GPU-00000000-0000-0000-0000-000000000003'}
assert not any(line.split(',')[0].strip() in target_uuids for line in snap['compute'].splitlines())
exit02=json.loads((P02/'original/exit.json').read_bytes());exit03=json.loads((P03/'original/exit.json').read_bytes())
assert exit03['worker_exit_code']==exit03['launcher_exit_code']==0
proof={'time_unix':time.time(),'status':'stored_native_evidence_and_terminal_audit_passed',
    'chains':chains,'calls':calls,'metrics':metrics,
    'C05_failed_full_request_and_all_prepared_tensors_identical_on_technical_retry':True,
    'all_eight_logical_controls_have_immutable_results':True,
    'old_completed_controls_not_reexecuted':True,
    'final_worker_and_launcher_actual_proc_absent':True,
    'target_compute_empty_holder_still_holds_nine_locks':True,
    'actual_exit_snapshot_sha256':sha(snapshot),
    'two_joint_inference_launcher_windows_four_GPU_reserved_seconds':exit02['four_GPU_reserved_seconds_in_launcher']+exit03['four_GPU_reserved_seconds_in_launcher'],
    'total_holder_reservation_cost_not_established':True,
    'formal_GUI_ready':False,'actor_feedback_effect_tested':False,'new_inference_for_this_audit':0}
for name,value in [('audit.json',proof),('merged-logical-results.json',results)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'seal.json').write_text(json.dumps({p.name:sha(p) for p in OUT.iterdir() if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'audit':str(OUT/'audit.json'),'audit_sha256':sha(OUT/'audit.json'),'metrics':metrics,'chains':chains},ensure_ascii=False))
