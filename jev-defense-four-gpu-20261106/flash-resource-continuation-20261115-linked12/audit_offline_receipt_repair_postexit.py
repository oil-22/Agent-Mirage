"""Read-only postexit audit of the approved offline10, including preserved failure.

--prepare-only compiles the readers and seals their source without contacting a
server. The actual audit requires the existing once-only submission and actual
worker/launcher exit. It cannot launch or retry models, GUI, Flash, or scoring.
"""
import argparse
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON


CASES = [1, 2, 17, 20, 29, 43, 44, 46, 47, 48]
PREP = HERE / 'approved-offline-receipt-repair-01'
PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-20261115-receipt-repair01'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-20261115-receipt-repair01'


ADMISSION = r'''
p=Path(PACKAGE);r=Path(OUTPUT);m=json.loads((p/'offline-manifest.json').read_bytes())
assert sha(p/'offline-manifest.json')==MANIFEST_SHA
for name,h in m['files'].items():assert sha(p/name)==h,name
assert m['output']==OUTPUT and m['max_new_primary_calls']==10 and m['extra_capacity_generations']==0
plan=json.loads((p/'development-plan.json').read_bytes());decision=json.loads((p/'authorization.json').read_bytes())
assert decision['authorized'] and sha(p/'development-plan.json')==decision['plan_sha256']
assert sha(p/'proposed-system-suffix.txt')==decision['suffix_sha256']
assert [v['case']for v in plan['inputs']]==CASES
assert not decision['formal_changed_GUI_authorized']
assert (r/'postexit-seal.json').exists() and (r/'exit.json').exists()
exit_record=json.loads((r/'exit.json').read_bytes());global_seal=json.loads((r/'postexit-seal.json').read_bytes())
assert global_seal and {str(f.relative_to(r))for f in r.rglob('*')if f.is_file()and f.name!='postexit-seal.json'}==set(global_seal)
records=[]
for f in [r/'launcher-process.json',r/'worker/process.json']:
 if not f.exists():continue
 record=json.loads(f.read_bytes());proc=Path('/proc',str(record['pid']));actual=identity(record['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==record[k]for k in ['pid','uid','command','start_ticks'])
 assert not same,'Offline worker/launcher remains live; wait on existing process'
 assert record['uid']==1033
 records.append({'file':str(f),'saved':record,'actual_if_PID_exists':actual,'same_live_process':False})
terminal=json.loads((r/'worker/terminal.json').read_bytes())if(r/'worker/terminal.json').exists()else None
if terminal:
 assert terminal['attempted_calls']<=10 and terminal['maximum_calls']==10
 assert terminal['completed_reply_cases']==CASES[:len(terminal['completed_reply_cases'])]
 assert terminal['extra_capacity_or_invariance_generations']==terminal['new_Flash_GUI_scorer_paid_calls']==0
 assert terminal['baseline_replays']==terminal['format_or_automatic_retries']==0
 assert terminal['reserved_GPU_count_for_cost']==8 and not terminal['formal_GUI_release']
 if terminal['status']=='completed':assert terminal['attempted_calls']==10 and terminal['completed_reply_cases']==CASES and exit_record['child_exit']==0
 else:assert terminal['status']=='preserved_failure'
else:assert exit_record['failure'] is not None,'No worker terminal or preserved launcher failure'
nonrequests={name:h for name,h in global_seal.items()if not name.startswith('worker/requests/')}
for name,h in nonrequests.items():assert sha(r/name)==h,name
proof,events=chain(r/'worker/journal/events.jsonl')if(r/'worker/journal/events.jsonl').exists()else(None,[])
if proof:assert not proof['ignored_partial_last_line']
calls=[v['data']for v in events if v['kind']=='approved_offline_call'];replies=[v['data']for v in events if v['kind']=='offline_reply_sealed']
assert [v['case']for v in calls]==CASES[:len(calls)] and [v['ordinal']for v in calls]==list(range(1,len(calls)+1))
assert [v['case']for v in replies]==CASES[:len(replies)]
if terminal:assert len(calls)==terminal['attempted_calls'] and [v['case']for v in replies]==terminal['completed_reply_cases']
folders=sorted((r/'worker/requests').glob('*'))if(r/'worker/requests').exists()else[]
assert len(folders)<=10 and all(f.name=='%02d'%n for f,n in zip(folders,sorted(CASES[:len(folders)])))
loaded=json.loads((r/'worker/loaded.json').read_bytes())if(r/'worker/loaded.json').exists()else None
if loaded:
 assert loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'and loaded['physical_gpus']==list(range(7))
 assert not loaded['main_history_truncation']and not loaded['image_preprocessing_changed']
 assert loaded['CUDA_LAUNCH_BLOCKING']=='1'and loaded['primary_allocator_memory_fraction']==0.87
 assert loaded['native_generation_backend_sha256']==m['files']['native/release/defense/qwen_backend.py']
 inventory=json.loads((r/'worker/all-parameters-and-buffers-before-device-audit.json').read_bytes())
 assert inventory and all(v['device']in['cuda:'+str(i)for i in range(7)]for v in inventory)
 assert all(v['dtype']=='torch.bfloat16'for v in inventory if v['kind']=='parameter')
assert exit_record['reserved_GPU_count']==8 and exit_record['ended']>=exit_record['began']
print(json.dumps({'time':time.time(),'package_manifest_sha256':MANIFEST_SHA,'frozen_source_files_verified':len(m['files']),
 'output_postexit_seal_sha256':sha(r/'postexit-seal.json'),'global_seal':global_seal,'nonrequest_files_freshly_verified':nonrequests,
 'actual_processes_exited':records,'exit':exit_record,'terminal':terminal,'loaded':loaded,'journal':proof,
 'approved_calls':calls,'sealed_replies':replies,'request_folders':[f.name for f in folders],
 'request_global_seal':{n:h for n,h in global_seal.items()if n.startswith('worker/requests/')},
 'reserved_seconds_scope':exit_record['reserved_seconds_scope'],
 'eight_GPU_reserved_seconds':8*(exit_record['ended']-exit_record['began']),
 'new_model_GPU_GUI_calls_by_audit':0,'not_walltime_currency_energy_or_savings':True}))
'''


REQUEST = r'''
import struct
p=Path(PACKAGE);r=Path(OUTPUT);d=r/'worker/requests'/('%02d'%CASE)
seal=json.loads((d/'seal.json').read_bytes());assert sha(d/'seal.json')==GLOBAL['worker/requests/'+d.name+'/seal.json']
verified={}
for name,h in seal.items():
 path=d/name;key='worker/requests/'+d.name+'/'+name
 assert GLOBAL[key]==h and sha(path)==h,name
 verified[key]=h
assert {f.name for f in d.iterdir()if f.is_file()and f.name!='seal.json'}==set(seal)
if CASE not in FINISHED:
 assert (d/'failure.json').exists()
 print(json.dumps({'case':CASE,'complete_reply':False,'preserved_technical_failure':True,
  'files_freshly_verified':verified,'seal_sha256':sha(d/'seal.json'),'no_semantic_label':True,'new_model_GPU_GUI_calls':0}))
else:
 assert not(d/'failure.json').exists()
 m=json.loads((p/'offline-manifest.json').read_bytes());plan=json.loads((p/'development-plan.json').read_bytes())
 frozen=next(v for v in plan['inputs']if v['case']==CASE);source=Path(frozen['proposed_full_body']).parent
 wrapper_path=p/'CPU-receipts'/('case-%02d.json'%CASE)
 assert sha(wrapper_path)==frozen['native_CPU_input_receipt_sha256']
 wrapper=json.loads(wrapper_path.read_bytes())
 assert wrapper['remote_case']==str(source)
 assert wrapper['remote_seal_sha256']==sha(source/'seal.json')==m['CPU_case_seals'][str(CASE)]
 assert wrapper['result']==json.loads((source/'result.json').read_bytes())
 assert sha(source/'seal.json')==m['CPU_case_seals'][str(CASE)]
 cpu=json.loads((source/'result.json').read_bytes());frozen_seal=json.loads((source/'seal.json').read_bytes())
 for name,h in frozen_seal.items():assert sha(source/name)==h,name
 assert sha(d/'body.json')==frozen['proposed_full_body_sha256']==cpu['proposed_full_body_sha256']
 body=json.loads((d/'body.json').read_bytes());binding=json.loads((d/'source-binding.json').read_bytes())
 old=Path(binding['original_request']);oldseal=json.loads((old/'seal.json').read_bytes())
 assert sha(old/'seal.json')==binding['original_request_seal_sha256']==cpu['source_request_seal_sha256']
 assert binding['case']==CASE and binding['approved_plan_sha256']==sha(p/'development-plan.json')
 assert sha(old/'body.json')==oldseal['body.json']==frozen['original_body_sha256']==cpu['source_body_sha256']
 original=json.loads((old/'body.json').read_bytes());suffix=(p/'proposed-system-suffix.txt').read_text('utf8')
 original['messages'][0]['content']+='\n\n'+suffix;assert original==body
 assert cpu['full_input_token_delta']==292 and cpu['full_original_PNGs_and_non_system_history_preserved']
 images=[]
 for message in body['messages']:
  if not isinstance(message['content'],list):continue
  for block in message['content']:
   if block.get('type')=='image_url':
    url=block['image_url']['url'];assert url.startswith('data:image/png;base64,')
    data=base64.b64decode(url.split(',',1)[1],validate=True);assert data.startswith(b'\x89PNG\r\n\x1a\n')
    images.append(hashlib.sha256(data).hexdigest())
 prepared=json.loads((d/'prepared.json').read_bytes());first=json.loads((d/'first-forward.json').read_bytes())
 expected=cpu['proposed_prepared'];assert set(prepared)==set(first)==set(expected)
 for key in expected:
  for field in ['shape','dtype','bytes','sha256']:assert prepared[key][field]==first[key][field]==expected[key][field],(key,field)
  for records in [prepared,first]:
   row=records[key];raw=d/row['file'];assert raw.stat().st_size==row['bytes']
   assert seal[row['file']]==row['sha256']
  assert json.loads((d/'frozen-CPU-prepared-match.json').read_bytes())[key]=={f:expected[key][f]for f in ['shape','dtype','bytes','sha256']}
  assert json.loads((d/'frozen-CPU-first-forward-match.json').read_bytes())[key]=={f:expected[key][f]for f in ['shape','dtype','bytes','sha256']}
 config=json.loads((d/'effective-generation.json').read_bytes());actual=json.loads((d/'actual-generation.json').read_bytes())
 native=json.loads((d/'native-call.json').read_bytes());response=json.loads((d/'response.json').read_bytes())
 assert sha(old/'effective-generation.json')==oldseal['effective-generation.json']
 assert config==json.loads((old/'effective-generation.json').read_bytes())==native['generation_config']
 assert config==json.loads((d/'original-effective-generation-match.json').read_bytes())
 assert config['max_new_tokens']==2048 and config['do_sample']is False
 counts=json.loads((d/'offline-generation-count.json').read_bytes());assert counts=={'generate_calls':1,'first_forward_seen':True}
 ids=actual['output_ids'];assert ids==native['generated_ids']and len(ids)==actual['output_tokens']and 0<len(ids)<=2048
 eos=config['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos;assert actual['natural_EOS']and ids[-1]in eos
 assert native['text']==response['text']and native['request_messages_sha256']==hashlib.sha256(canonical(body['messages'])).hexdigest()
 assert response['case']==CASE and response['GUI_Flash_scorer_calls']==0 and response['proposed_action_not_executed']
 assert native['environment_actions_executed']is False and not native['hit_output_cap']
 input_record=prepared['input_ids'];assert input_record['dtype']=='torch.int64'and input_record['shape'][0]==1
 raw=(d/input_record['file']).read_bytes();input_ids=list(struct.unpack('<'+'q'*(len(raw)//8),raw))
 assert input_ids==native['input_ids']and len(input_ids)==actual['input_tokens']
 assert sha(old/'actual-generation.json')==oldseal['actual-generation.json']
 assert actual['input_tokens']==json.loads((old/'actual-generation.json').read_bytes())['input_tokens']+292
 sequence=(d/'sequence_ids.tensor').read_bytes();sequence_ids=list(struct.unpack('<'+'q'*(len(sequence)//8),sequence))
 assert sequence_ids==input_ids+ids
 assert actual['actual_forward_calls']==json.loads((d/'forward-count.json').read_bytes())['actual_forward_calls']>0
 assert expected['image_grid_thw']['shape'][0]==len(images)
 worker=json.loads((r/'worker/process.json').read_bytes())
 lease=json.loads((r/'offline-lease.json').read_bytes());expected_uuid={v['index']:v['uuid']for v in lease['gpu']}
 for admission in ['admission-before.json','admission-after.json']:
  record=json.loads((d/admission).read_bytes());assert record['held_GPU_or_group_locks']==17 and record['inference_mutex_inherited']
  assert record['actually_reserved_GPU_count_for_cost']==8 and record['main_physical_GPUs']==list(range(7))
  assert not record['Flash_started']and record['GPU7_reserved_by_original_lease_but_idle']
  snap=record['snapshot'];uuids={v['uuid']:int(k)for k,v in snap['gpu'].items()}
  assert {int(k):v['uuid']for k,v in snap['gpu'].items()}==expected_uuid
  assert {uuids[v['uuid']]for v in snap['compute']}==set(range(7))and len(snap['compute'])==7
  for v in snap['compute']:assert all(v['identity'][f]==worker[f]for f in ['pid','uid','command','start_ticks'])
 print(json.dumps({'case':CASE,'complete_reply':True,'seal_sha256':sha(d/'seal.json'),
  'files_freshly_verified':verified,'prepared_CPU_first_forward_raw_all_equal':True,
  'full_original_history_PNGs_preserved':True,'image_sha256_order':images,'input_tokens':actual['input_tokens'],
  'output_tokens':len(ids),'natural_EOS':True,'native_seconds':native['seconds'],'actual_input_token_delta':292,
  'same_original_effective_generation':True,'approved_suffix_only':True,
  'one_generate_call':True,'proposed_action_not_executed':True,
  'admission_before_after_owned_compute_and_inherited_locks_verified':True,
  'no_semantic_label_inferred':True,'new_model_GPU_GUI_calls':0}))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    package = PREP / 'package'
    manifest_sha = sha(package / 'offline-manifest.json')
    prefix = ('PACKAGE=' + repr(PACKAGE) + '\nOUTPUT=' + repr(OUTPUT) + '\nCASES=' + repr(CASES)
              + '\nMANIFEST_SHA=' + repr(manifest_sha) + '\n')
    compile(prefix + COMMON + ADMISSION, '<offline-postexit-admission>', 'exec')
    compile(prefix + COMMON + REQUEST, '<offline-postexit-one-case>', 'exec')
    if args.prepare_only:
        dest = HERE / ('offline10-audit-preparation-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        save(dest / 'preparation.json', {
            'time': time.time(), 'readers_compiled_only': True, 'source_manifest_sha256': manifest_sha,
            'actual_postexit_audit_executed': False, 'existing_submission_required': True,
            'requires_actual_offline_worker_launcher_exit': True,
            'full_actual_input_CPU_forward_sequence_EOS_file_and_journal_checks_prepared': True,
            'preserved_failure_not_semantic_zero': True, 'experiment_sources_changed': False,
            'new_model_GPU_GUI_calls': 0, 'semantic_or_effectiveness_claim': False})
        save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(dest), 'actual_audit_executed': False, 'new_model_GPU_GUI_calls': 0}))
        return
    assert (PREP / 'submission.json').exists(), 'Do not launch from this inspector; wait for approved once-only submission'
    raw, operation = remote('3090', prefix + COMMON + ADMISSION, 'approved-offline10-postexit-admission', timeout=55)
    admission = json.loads(raw)
    dest = HERE / ('offline10-receipt-repair-postexit-audit-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'admission.json', {'result': admission, 'operation': str(operation)})
    finished = admission['terminal']['completed_reply_cases'] if admission['terminal'] else []
    rows, checked = [], dict(admission['nonrequest_files_freshly_verified'])
    for name in admission['request_folders']:
        number = int(name)
        code = (prefix + '\nCASE=' + repr(number) + '\nFINISHED=' + repr(finished)
                + '\nGLOBAL=' + repr(admission['global_seal']) + '\n' + COMMON + REQUEST)
        raw, operation = remote('3090', code, 'approved-offline10-complete-raw-case-' + name, timeout=55)
        result = json.loads(raw)
        checked.update(result['files_freshly_verified'])
        key = 'worker/requests/' + name + '/seal.json'
        checked[key] = result['seal_sha256']
        save(dest / ('case-' + name + '.json'), {'result': result, 'operation': str(operation)})
        rows.append(result)
        print(json.dumps({'case_verified': number, 'complete_reply': result['complete_reply'],
                          'new_model_GPU_GUI_calls': 0}), flush=True)
    assert checked == admission['global_seal']
    assert [v['case'] for v in rows if v['complete_reply']] == finished
    save(dest / 'summary.json', {
        'time': time.time(), 'all_original_postexit_files_freshly_verified': len(checked),
        'actual_existing_worker_launcher_exits_verified': True, 'attempted_calls': len(admission['approved_calls']),
        'completed_reply_cases': finished, 'preserved_failure': len(finished) != 10,
        'new_Flash_GUI_scorer_paid_calls': 0, 'automatic_or_format_retries': 0,
        'reserved_GPU_count': 8, 'eight_GPU_reserved_seconds': admission['eight_GPU_reserved_seconds'],
        'input_tokens': sum(v.get('input_tokens', 0) for v in rows),
        'output_tokens': sum(v.get('output_tokens', 0) for v in rows),
        'summed_native_seconds': sum(v.get('native_seconds', 0) for v in rows),
        'not_walltime_currency_energy_or_savings': True, 'new_model_GPU_GUI_calls_by_audit': 0,
        'source_semantic_review_and_formal_condition_decision_still_required': True,
        'Mirage_reduction': None, 'effectiveness_proven': False, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    save(HERE / 'offline10-receipt-repair-postexit-audit-current.json', {'audit': str(dest),
         'seal_sha256': sha(dest / 'seal.json'), 'time': time.time(), 'effectiveness_proven': False})
    print(json.dumps({'audit': str(dest), 'complete_replies': len(finished),
                      'freshly_verified_files': len(checked), 'new_model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
