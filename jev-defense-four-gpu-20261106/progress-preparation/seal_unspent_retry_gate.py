"""Seal independent unspent service and completed before-begin GUI failure evidence."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / 'progress-preparation/progress_remote.py'
GROUP = '/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243'
GUI = '/data/researcher/jev-defense-four-gpu-20261106'

SERVICE_AUDIT = '''
group = Path(GROUP_PATH)
snapshot = service_snapshot(group)
assert snapshot['holder']['identity_matches'] and snapshot['launcher']['identity_matches']
assert snapshot['all_actual_peer_identities_valid'] and not snapshot['foreign_target_compute']
assert not snapshot['launcher_failure_present'] and not snapshot['transitions']
state = snapshot['state_snapshot']
assert state['phase']=='ready' and state['active'] is None and state['next_run_index']==0
assert len(state['runs'])==4
assert all(r['status']=='not_started' and r['last_decision_index']==0 and
    r['calls']=={'actor':0,'judge':0,'observe':0} for r in state['runs'].values())
assert snapshot['journal']['event_count']==2 and snapshot['journal']['kind_counts']=={'worker_loaded':2}
assert snapshot['journal']['uncommitted_partial_tail_bytes']==0
assert all(not row['requests'] and len(row['actual_locks'])==9 for row in snapshot['workers'].values())
files={'original-online-state.json':base64.b64encode((group/'online-state.json').read_bytes()).decode(),
       'original-online-journal.jsonl':base64.b64encode((group/'journal.jsonl').read_bytes()).decode()}
print(json.dumps({'passed':True,'time':time.time(),'snapshot':snapshot,'files':files,
    'read_only':True,'HTTP_model_GUI_calls':0}))
'''
CONTROLLER_AUDIT = '''
base=Path(GUI_PATH);batch=base/'gui-batch-image-observer-01';control=base/'gui-outer-control-01'
snapshot=controller_snapshot(batch,control,base/'gui-outer-background-01')
assert snapshot['status_snapshot']['phase']=='failed' and snapshot['status_snapshot']['completed']==0
assert not snapshot['eventchains'] and snapshot['outer_finalization_present'] and snapshot['outer_postexit_seal_present']
assert all(not row['identity_matches'] and row['actual'] is None for row in snapshot['processes'].values())
failure=read(batch/'uncaught-failure.json');finalization=read(control/'finalization.json')
assert "KeyError: 'DATASET'" in failure['traceback']
assert finalization['exit_code']==1 and finalization['all_four_complete'] is False
assert finalization['execution_completed'] is False and finalization['no_automatic_retry'] is True
files={}
for prefix,root,manifest in [('batch',batch,control/'batch-postexit-sha256.json'),
                             ('control',control,control/'postexit-sha256.json')]:
    mapping=read(manifest)
    if prefix=='batch': assert set(mapping)<= {'batch.lock','status.json','uncaught-failure.json'}
    for name,expected in mapping.items():
        relative=Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        assert sha(root/relative)==expected
    files[prefix+'-postexit-manifest.json']=base64.b64encode(manifest.read_bytes()).decode()
for name,path in [('original-uncaught-failure.json',batch/'uncaught-failure.json'),
    ('original-finalization.json',control/'finalization.json'),
    ('original-controller-status.json',batch/'status.json')]:
    files[name]=base64.b64encode(path.read_bytes()).decode()
print(json.dumps({'passed':True,'time':time.time(),'snapshot':snapshot,'files':files,
    'failure_sha256':sha(batch/'uncaught-failure.json'),'no_PRIVATE_answer_files_read':True,
    'old_batch_and_control_postexit_manifests_verified':True,'HTTP_model_GUI_calls':0}))
'''


def collect(host, extra):
    code = "__name__ = 'audit_helpers'\nimport base64\nGROUP_PATH=" + repr(GROUP) + '\nGUI_PATH=' + repr(GUI) + '\n'
    code += SOURCE.read_text(encoding='utf8') + '\n' + extra
    return json.loads(remote(code, timeout=90, host=host))


def main():
    root = BASE / 'gui-before-begin-unspent-proof' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {'service3090':pool.submit(collect,'3090',SERVICE_AUDIT),
                   'controller4090':pool.submit(collect,'4090',CONTROLLER_AUDIT)}
        records = {key: future.result() for key, future in futures.items()}
    for key, value in records.items():
        dest = root / key; dest.mkdir()
        for name, encoded in value.pop('files').items():
            (dest / name).write_bytes(base64.b64decode(encoded))
        (dest / 'actual-snapshot.json').write_text(json.dumps(value,indent=2),encoding='utf8')
    receipt = {'status':'passed','classification':'completed_GUI_before_begin_infrastructure_failure_unspent_services',
        'old_GUI_failure':'KeyError DATASET during original native environment import',
        'old_GUI_batch':GUI+'/gui-batch-image-observer-01','old_GUI_control':GUI+'/gui-outer-control-01',
        'service_group':GROUP,'actual_services_kept_loaded':True,
        'actual_UID_fullcmd_startticks_all9locks_verified':True,'foreign_target_compute_count':0,
        'exact_service_journal_two_worker_loaded_events':True,'service_requests':0,'service_transitions':0,
        'all_four_runs_not_started':True,'all_run_actor_judge_observer_counts_zero':True,
        'old_Controller_event_count':0,'old_GUI_begin_count':0,'old_GUI_exit_code':1,
        'old_GUI_postexit_seals_verified':True,'old_GUI_failed_no_automatic_retry_retained':True,
        'scope':'gate evidence for separately authorized linked infrastructure retry only; no old root/claim reuse',
        'readiness_receipt_sha256':'f30b0ef2655c82fe17a4c67afa983244647a49ef32719a90b6e0b9b619f1a215',
        'no_model_GUI_semantic_success_claim':True,'new_HTTP_model_GUI_calls':0,
        'snapshots_not_atomic_across_hosts':True,'times':{key:value['time'] for key,value in records.items()}}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    (root/'auditor-source.py').write_bytes(Path(__file__).read_bytes())
    (root/'progress-helper-source.py').write_bytes(SOURCE.read_bytes())
    seal = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob('*') if p.is_file()}
    (root/'seal.json').write_text(json.dumps(seal,indent=2),encoding='utf8')
    print(json.dumps({'proof_root':str(root),'receipt_sha256':seal['receipt.json'],
        'seal_sha256':hashlib.sha256((root/'seal.json').read_bytes()).hexdigest(),
        'status':'passed','service_requests':0,'service_transitions':0,'Controller_events':0,
        'old_GUI_exit_code':1,'new_HTTP_model_GUI_calls':0}))


if __name__=='__main__':
    main()
