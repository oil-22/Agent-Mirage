"""Read-only, strict all-29 admission across the stopped parent and its continuation.

No models, screenshots, actions, scorers, GPU leases, old queues or labels are
started by this reader. A running/incomplete continuation fails admission.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from control import HERE, R3090, OUT, R4090, remote, save, sha
from capture_live_evidence import COMMON

from offline_followup_control import PREP
sys.path.insert(0, str(PREP / 'package'))
from aggregate_completion import validate_cover


NATIVE = r'''
b=BINDINGS;old=Path(b['parent_output']);pold=Path(b['parent_package']);r=Path(b['continuation_output']);p=Path(b['continuation_package'])
assert sha(old/'postexit-seal.json')==b['parent_postexit_seal_sha256']
for source,expected in [(pold,b['parent_manifest_sha256']),(p,b['continuation_manifest_sha256'])]:
 assert sha(source/'manifest.json')==expected
 for name,h in json.loads((source/'manifest.json').read_bytes())['files'].items():assert sha(source/name)==h
parent_status=json.loads((old/'primary/status.json').read_bytes());assert parent_status['phase']=='technical_failure'and parent_status['done']==16 and parent_status['attempted_actor_calls']==397 and parent_status['complete_actor_replies']==396
status=json.loads((r/'primary/status.json').read_bytes());terminal=json.loads((r/'primary/terminal.json').read_bytes());group=json.loads((r/'exit.json').read_bytes())
assert status['phase']=='completed'and status['done']==status['expected']==13 and status['active']is None
assert terminal['status']=='completed'and terminal['done']==terminal['expected']==13
assert terminal['attempted_actor_calls']==terminal['complete_actor_replies']
assert group['exit_code']==0 and group['failure']is None and all(v['exit_code']==0 for v in group['children'])
processes=[]
for path in [old/'launcher-process.json',old/'primary/process.json',pold/'flash/service/process.json',r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']:
 saved=json.loads(path.read_bytes());proc=Path('/proc',str(saved['pid']));actual=identity(saved['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
 assert not same,'A model/launcher remains live; no offline admission'
 processes.append({'saved':saved,'actual_if_PID_exists':actual,'same_live_process':False})
post=json.loads((r/'postexit-seal.json').read_bytes())
actual={str(f.relative_to(r))for f in r.rglob('*')if f.is_file()and f.name!='postexit-seal.json'}|{str(f.relative_to(p))for f in(p/'flash/service').rglob('*')if f.is_file()and f.name!='token'}
assert set(post)==actual
for name in ['primary/status.json','primary/terminal.json','exit.json','expanded-lease.json']:
 assert sha(r/name)==post[name]
requests=list((r/'primary/requests').glob('*'));assert len(requests)==terminal['complete_actor_replies']
for d in requests:
 assert(d/'response.json').exists()and not(d/'failure.json').exists()
 assert sha(d/'seal.json')==post[str((d/'seal.json').relative_to(r))]
print(json.dumps({'time':time.time(),'parent_native_postexit_seal_sha256':sha(old/'postexit-seal.json'),'continuation_native_postexit_seal_sha256':sha(r/'postexit-seal.json'),'actual_model_and_launcher_processes_exited':True,'processes':processes,'status':status,'terminal':terminal,'group':group,'postexit_complete_file_set_verified':True,'raw_files_fresh_rehash_NOT_claimed_by_admission':True,'new_model_GPU_GUI_calls':0}))
'''

GUI = r'''
base=Path('/data/researcher/jev-defense-four-gpu-20261106');old=base/'flash-ample-memory-gui-20261114-linked11';r=base/'flash-resource-continuation-20261115-linked12'
assert sha(old/'manifest.json')==BINDINGS['parent_manifest_sha256']and sha(r/'manifest.json')==BINDINGS['continuation_manifest_sha256']
parent_status=json.loads((old/'batch/status.json').read_bytes());status=json.loads((r/'batch/status.json').read_bytes())
assert parent_status['phase']=='technical_failure'and parent_status['completed']==16 and parent_status['processed']==17 and parent_status['expected']==29
assert status['phase']=='completed'and status['completed']==status['processed']==status['expected']==13
processes=[];controls=[]
for root in [old,r]:
 for name in ['control/process.json','control/runner-process.json']:
  saved=json.loads((root/name).read_bytes());proc=Path('/proc',str(saved['pid']));actual=identity(saved['pid'])if proc.exists()else None
  same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
  assert not same,'GUI still active; no offline admission'
  processes.append({'saved':saved,'actual_if_PID_exists':actual,'same_live_process':False})
 assert json.loads((root/'control/exit.json').read_bytes())['child_exit']==0
 seal=json.loads((root/'control/postexit-seal.json').read_bytes())
 for name,h in seal.items():assert sha(root/'control'/name)==h
 controls.append({'root':str(root),'control_postexit_seal_sha256':sha(root/'control/postexit-seal.json')})
rows=[]
for label,root in [('parent',old),('continuation',r)]:
 paths=sorted((root/'batch/runs').glob('*/attempt-*/terminal.json'));assert len(paths)==(17 if label=='parent'else 13)
 for path in paths:
  t=json.loads(path.read_bytes());assert(path.parent/'seal.json').exists()
  rows.append({'group':label,'run_id':t['run']['run_id'],'terminal':str(path),'terminal_sha256':sha(path),'seal_sha256':sha(path.parent/'seal.json'),'infrastructure_failure':t['infrastructure_failure'],'cleanup_error':t.get('cleanup_error'),'outcome':t['outcome'],'official_reward':t['official_reward']})
print(json.dumps({'time':time.time(),'terminals':rows,'actual_GUI_processes_exited':True,'processes':processes,'control_seals':controls,'parent_GUI_phase':parent_status['phase'],'continuation_GUI_phase':status['phase'],'parent_GUI_child_exit':0,'continuation_GUI_child_exit':0,'new_model_GPU_GUI_calls':0}))
'''

TERMINALS = r'''
out=[]
for row in ROWS:
 path=Path(row['terminal']);d=path.parent;assert sha(path)==row['terminal_sha256']and sha(d/'seal.json')==row['seal_sha256']
 seal=json.loads((d/'seal.json').read_bytes())
 for name,h in seal.items():assert sha(d/name)==h
 assert{str(f.relative_to(d))for f in d.rglob('*')if f.is_file()and f.name!='seal.json'}==set(seal)
 proof,events=chain(d/'controller/events.jsonl');assert not proof['ignored_partial_last_line']
 t=json.loads(path.read_bytes());assert t['run']['run_id']==row['run_id']and t['infrastructure_failure']==row['infrastructure_failure']and t.get('cleanup_error')==row['cleanup_error']
 out.append({**row,'seal_verified':True,'chain_verified':True,'chain_head':proof['head'],'events':proof['verified_prefix_events'],'sealed_files_verified':len(seal)})
print(json.dumps(out))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    b = json.loads((PREP / 'package/aggregate-bindings.json').read_bytes())
    prefix = 'BINDINGS=' + repr(b) + '\n' + COMMON
    for name, code in [('native', NATIVE), ('GUI', GUI), ('terminals', TERMINALS)]:
        compile(prefix + code, '<aggregate-' + name + '>', 'exec')
    if args.prepare_only:
        root = HERE / ('aggregate-admission-reader-preparation-' + str(time.time_ns()))
        root.mkdir()
        (root / 'source.py').write_bytes(Path(__file__).read_bytes())
        save(root / 'preparation.json', {'time': time.time(), 'readers_compiled_only': True,
             'actual29_terminal_or_model_exit_admission_not_executed': True,
             'requires_parent16_normal_plus_preserved1technical_plus_continuation13_normal': True,
             'all10_actual_old_and_new_model_GUI_launcher_exits_required': True,
             'full_all30_GUI_attempt_file_seals_and_chains_required': True,
             'old_parent_not_relabelled_success': True, 'new_model_GPU_GUI_calls': 0})
        save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(root), 'actual_admission_executed': False, 'new_model_GPU_GUI_calls': 0}))
        return
    assert not (HERE / 'aggregate-completion-current.json').exists(), 'Inspect the sealed existing completion; never rerun it'
    raw, op = remote('3090', prefix + NATIVE, 'actual-parent-and-continuation-model-completion-required')
    native = json.loads(raw)
    root = HERE / ('aggregate-GUI-completion-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'native.json', {'result': native, 'operation': str(op)})
    raw, op = remote('4090', prefix + GUI, 'actual-all29-logical-GUI-completion-and-exits-required')
    gui = json.loads(raw)
    save(root / 'GUI.json', {'result': gui, 'operation': str(op)})
    verified = []
    for start in range(0, len(gui['terminals']), 5):
        raw, op = remote('4090', 'ROWS=' + repr(gui['terminals'][start:start + 5]) + '\n' + COMMON + TERMINALS,
                         'all30-attempts-fresh-seals-and-chains-' + str(start), timeout=55)
        rows = json.loads(raw)
        verified.extend(rows)
        save(root / ('terminals-%02d.json' % start), {'result': rows, 'operation': str(op)})
    parent = [v for v in verified if v['group'] == 'parent']
    current = [v for v in verified if v['group'] == 'continuation']
    expected = [v['run_id'] for v in json.loads((PREP / 'package/native/plan.json').read_bytes())['queue']]
    normal, technical = validate_cover(parent, current, expected, b['contract'])
    original_rows = json.loads((HERE / 'package/parent-bindings.json').read_bytes())['GUI_terminals']
    for actual in parent:
        before = next(v for v in original_rows if v['run_id'] == actual['run_id'])
        assert actual['terminal_sha256'] == before['terminal_sha256'] and actual['seal_sha256'] == before['seal_sha256']
        assert actual['chain_head'] == before['chain']['head'] and actual['events'] == before['chain']['verified_prefix_events']
    admission = {**{k: native[k] for k in ['parent_native_postexit_seal_sha256', 'continuation_native_postexit_seal_sha256', 'actual_model_and_launcher_processes_exited']},
                 **{k: gui[k] for k in ['actual_GUI_processes_exited', 'parent_GUI_child_exit', 'continuation_GUI_child_exit', 'parent_GUI_phase', 'continuation_GUI_phase']},
                 'time': time.time(), 'parent_manifest_sha256': b['parent_manifest_sha256'],
                 'continuation_manifest_sha256': b['continuation_manifest_sha256'],
                 'parent_terminals': parent, 'continuation_terminals': current,
                 'terminals': normal, 'preserved_technical_attempts': technical,
                 'failed_partial_costs_and_source_occurrences_retained': True,
                 'stopped_parent_relabelled_completed': False,
                 'source_metadata_admission_only_not_fresh_native_raw_or_controller_final_audit': True,
                 'new_model_GPU_GUI_calls': 0, 'effectiveness_proven': False}
    save(root / 'admission.json', admission)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'aggregate-completion-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'time': time.time()})
    print(json.dumps({'completion_admission': str(root), 'normal_logical_configurations': 29, 'preserved_technical_attempts': 1, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
