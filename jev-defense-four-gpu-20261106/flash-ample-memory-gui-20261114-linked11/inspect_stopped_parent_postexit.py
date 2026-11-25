"""Verify stopped-parent exits, global manifest identity and all GUI terminals.

This metadata reader does not claim a fresh full rehash of old raw tensors.
It cannot launch or retry a model/GUI, acquire a GPU lease, or change a label.
"""
import json
import time
from control import HERE, R3090, OUT, R4090, remote, save, sha
from capture_live_evidence import COMMON


def main():
    root = HERE / ('stopped-parent-postexit-metadata-' + str(time.time_ns()))
    root.mkdir()
    (root / 'inspector-source.py').write_bytes(__import__('pathlib').Path(__file__).read_bytes())
    code = 'ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\n' + COMMON + r'''
r=Path(ROOT);p=Path(PACKAGE);processes=[]
for f in [r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']:
 record=json.loads(f.read_bytes());proc=Path('/proc',str(record['pid']));actual=identity(record['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==record[k]for k in ['uid','command','start_ticks'])
 assert not same;processes.append({'saved':record,'actual_if_PID_exists':actual,'same_live_process':False})
post=r/'postexit-seal.json';before=post.stat();global_seal=json.loads(post.read_bytes());posthash=sha(post);after=post.stat()
assert(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
manifest=json.loads((p/'manifest.json').read_bytes());assert sha(p/'manifest.json')=='5e7e068ac14d75d668dfeca28ac7af61cf304e73187b21ed91169e9bb06c4762'
assert all(sha(p/n)==h for n,h in manifest['files'].items())
exit=json.loads((r/'exit.json').read_bytes());assert exit['exit_code']==1 and exit['failure']is None
status=json.loads((r/'primary/status.json').read_bytes());assert status['phase']=='technical_failure'and status['done']==16 and status['attempted_actor_calls']==397 and status['complete_actor_replies']==396
actual_names={str(f.relative_to(r))for f in r.rglob('*')if f.is_file()and f.name!='postexit-seal.json'}|{str(f.relative_to(p))for f in(p/'flash/service').rglob('*')if f.is_file()and f.name!='token'}
assert set(global_seal)==actual_names
seals=[]
for d in sorted((r/'primary/requests').iterdir()):
 if not d.is_dir():continue
 relative=str((d/'seal.json').relative_to(r));assert sha(d/'seal.json')==global_seal[relative]
 local=json.loads((d/'seal.json').read_bytes())
 assert{str(d.relative_to(r))+'/'+n:h for n,h in local.items()}=={n:h for n,h in global_seal.items()if n.startswith(str(d.relative_to(r))+'/')and n!=relative}
 seals.append({'name':d.name,'seal_sha256':global_seal[relative],'public_response':(d/'response.json').exists(),'failure':(d/'failure.json').exists()})
assert len(seals)==397 and sum(v['public_response']for v in seals)==396 and sum(v['failure']for v in seals)==1
flash_seals=[]
for d in sorted((p/'flash/service/requests').iterdir()):
 relative=str((d/'seal.json').relative_to(p));assert sha(d/'seal.json')==global_seal[relative]
 flash_seals.append({'request_id':d.name,'seal_sha256':global_seal[relative]})
assert len(flash_seals)==199
import subprocess
GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
print(json.dumps({'time':time.time(),'actual_parent_processes_exited':processes,'postexit_seal_sha256':posthash,'postexit_manifest_files':len(global_seal),'postexit_manifest_entries':global_seal,'current_global_file_set_matches':True,'per_request_seal_identities_and_global_membership_verified':seals,'Flash_seal_identities':flash_seals,'full_old_raw_files_NOT_freshly_rehashed_by_this_metadata_reader':True,'frozen_sources_verified':len(manifest['files']),'manifest_sha256':sha(p/'manifest.json'),'capacity_seal_sha256':sha(r/'capacity/seal.json'),'exit':exit,'status':status,'GPU':GPU,'compute':compute,'new_model_GUI_calls':0}))
'''
    compile(code, '<stopped-parent-metadata>', 'exec')
    raw, op = remote('3090', code, 'stopped-parent-actual-exit-global-manifest-and-seal-identities', timeout=55)
    native = json.loads(raw)
    save(root / '3090.json', {'result': native, 'operation': str(op)})
    code = 'ROOT=' + repr(R4090) + '\n' + COMMON + r'''
r=Path(ROOT);procs=[]
for name in ['control/process.json','control/runner-process.json']:
 v=json.loads((r/name).read_bytes());proc=Path('/proc',str(v['pid']));actual=identity(v['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==v[k]for k in ['uid','command','start_ticks']);assert not same
 procs.append({'saved':v,'actual_if_PID_exists':actual,'same_live_process':False})
rows=[]
for tfile in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):
 d=tfile.parent;t=json.loads(tfile.read_bytes());seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/n)==h for n,h in seal.items())
 proof,events=chain(d/'controller/events.jsonl');assert not proof['ignored_partial_last_line']
 rows.append({'run_id':t['run']['run_id'],'terminal':str(tfile),'terminal_sha256':sha(tfile),'seal_sha256':sha(d/'seal.json'),'infrastructure_failure':t['infrastructure_failure'],'outcome':t['outcome'],'official_reward':t['official_reward'],'cleanup_error':t.get('cleanup_error'),'chain':proof})
assert len(rows)==17 and sum(not v['infrastructure_failure']for v in rows)==16 and all(v['cleanup_error']is None for v in rows)
ctrl=json.loads((r/'control/postexit-seal.json').read_bytes());assert all(sha(r/'control'/n)==h for n,h in ctrl.items())
status=json.loads((r/'batch/status.json').read_bytes());assert status['phase']=='technical_failure'and status['completed']==16 and status['processed']==17
print(json.dumps({'time':time.time(),'actual_GUI_processes_exited':procs,'control_postexit_files_verified':len(ctrl),'control_postexit_seal_sha256':sha(r/'control/postexit-seal.json'),'terminals':rows,'batch_status':status,'new_model_GUI_calls':0}))
'''
    compile(code, '<stopped-GUI-metadata>', 'exec')
    raw, op = remote('4090', code, 'stopped-parent-GUI-actual-exit-all17-terminal-seals-and-chains', timeout=55)
    gui = json.loads(raw)
    save(root / '4090.json', {'result': gui, 'operation': str(op)})
    plan = json.loads((HERE / 'package/plan.json').read_bytes())
    normal = {v['run_id'] for v in gui['terminals'] if not v['infrastructure_failure']}
    failed = [v for v in gui['terminals'] if v['infrastructure_failure']]
    remaining = [v for v in plan['queue'] if v['run_id'] not in normal]
    assert len(remaining) == 13 and len(failed) == 1 and remaining[0]['run_id'] == failed[0]['run_id']
    save(root / 'technical-continuation-contract.json', {
        'time': time.time(), 'phase': 'contract_preparation_only_not_launched',
        'original_manifest_sha256': native['manifest_sha256'],
        'parent_postexit_seal_sha256': native['postexit_seal_sha256'],
        'GUI_control_postexit_seal_sha256': gui['control_postexit_seal_sha256'],
        'normal_completed_run_ids': sorted(normal), 'failed_attempt_preserved': failed[0],
        'remaining_queue': remaining, 'original_total_logical_configurations': 29,
        'new_linked_attempt_required': True,
        'never_restart_original_queue_or_reexecute_16_completed_terminals': True,
        'failed_T089_source_positive_remains_in_any_logical_aggregate_despite_retry': True,
        'parent_partial_attempt_costs_and_actions_remain_separate_not_erased': True,
        'original_per_attempt_limits': {'decisions': 50, 'actor_calls': 70, 'actor_output': 2048},
        'all_original_main_prompt_and_history_image_and_generation_conditions_retained': True,
        'Flash_single_image_fixed_prompt_yes_no_stateless_unchanged': True,
        'fresh_GPU_ownership_UUID_compute_free_memory_and_inherited_locks_required_before_launch': True,
        'completed_capacity_controls_not_reexecuted': True,
        'capacity_source_proof_reuse_requires_exact_native_and_patch_source_binding_not_a_fresh_current_process_capacity_claim': True,
        'offline10_approval_preserved_not_launched': True,
        'new_model_GUI_calls': 0, 'goal': 'active',
    })
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'metadata': str(root), 'all_original_model_launcher_GUI_processes_exited': True,
        'parent_postexit_files': native['postexit_manifest_files'],
        'parent_postexit_seal_sha256': native['postexit_seal_sha256'],
        'actual_GPU': native['GPU'], 'actual_compute': native['compute'],
        'GUI_terminals': len(gui['terminals']), 'remaining13_contract_frozen': True,
        'full_old_raw_fresh_rehash_not_claimed': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
