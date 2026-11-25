"""Submit one linked metadata repair with the original, wholly unused ten calls."""
import json
from pathlib import Path
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON
from offline_followup_control import PREP as PRIOR
from prepare_offline_receipt_repair import PREP, PACKAGE, REMOTE, OUTPUT


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    assert not (PREP / 'submission.json').exists(), 'Inspect the existing linked run; never resubmit'
    controls = load(PREP / 'CPU-binding-controls.json')['result']
    assert controls['passed'] == 12 and controls['manifest_sha256'] == sha(PACKAGE / 'offline-manifest.json')
    assert load(PREP / 'stage-receipt.json')['result']['all10_approved_wrapper_to_original_remote_result_bindings_passed']
    pointer = load(HERE / 'aggregate-completion-current.json')
    root = Path(pointer['root'])
    assert root.parent == HERE and sha(root / 'seal.json') == pointer['seal_sha256']
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    admission = load(root / 'admission.json')
    assert len(admission['terminals']) == 29 and len(admission['preserved_technical_attempts']) == 1
    code = 'ADMISSION=' + repr(admission) + '\n' + COMMON + r'''
base=Path('/data/researcher/jev-defense-four-gpu-20261106');proof=[]
for label,name in [('parent','flash-ample-memory-gui-20261114-linked11'),('continuation','flash-resource-continuation-20261115-linked12')]:
 r=base/name;s=json.loads((r/'batch/status.json').read_bytes())
 assert s['phase']==('technical_failure'if label=='parent'else'completed')
 assert s['completed']==(16 if label=='parent'else 13)and s['processed']==(17 if label=='parent'else 13)
 assert json.loads((r/'control/exit.json').read_bytes())['child_exit']==0
 for n in ['control/process.json','control/runner-process.json']:
  saved=json.loads((r/n).read_bytes());actual=identity(saved['pid'])if Path('/proc',str(saved['pid'])).exists()else None
  same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
  assert not same;proof.append({'saved':saved,'actual_if_PID_exists':actual,'same_live':False})
 for row in ADMISSION[label+'_terminals']:
  q=Path(row['terminal']);assert q.resolve().is_relative_to(r.resolve())
  assert sha(q)==row['terminal_sha256']and sha(q.parent/'seal.json')==row['seal_sha256']
print(json.dumps({'time':time.time(),'actual_GUI_exits':proof,'all30_attempt_terminal_seal_identities_unchanged':True,'new_model_GPU_GUI_calls':0}))
'''
    raw, gui_op = remote('4090', code, 'linked-receipt-repair-fresh-GUI-exits-and-terminal-identities')
    gui = json.loads(raw)
    old_submission = load(PRIOR / 'submission.json')['result']
    command_name = 'evidence-discipline-offline-development-20261114-01-receipt-repair01.json'
    code = ('PACKAGE=' + repr(REMOTE) + '\nOUTPUT=' + repr(OUTPUT)
        + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json'))
        + '\nADMISSION=' + repr(admission) + '\nOLD_COMMAND=' + repr(old_submission['command'])
        + '\nOLD_COMMAND_SHA=' + repr(old_submission['command_sha256'])
        + '\nCOMMAND_NAME=' + repr(command_name) + '\n' + r'''
import json,os,sys,time
from pathlib import Path
assert os.getuid()==1033
p=Path(PACKAGE);sys.path.insert(0,str(p));import offline_guard as g
from receipt_binding import verify_cpu_receipt,verify_zero_call_parent
assert g.sha(p/'offline-manifest.json')==EXPECTED
m,plan=g.verify_package();parent=verify_zero_call_parent(p)
assert parent['prior_attempted_calls']==0 and not Path(OUTPUT).exists()
assert not Path('/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-development-20261114-01').exists()
assert g.sha(p/'development-plan.json')=='98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a'
for frozen in plan['inputs']:verify_cpu_receipt(p,Path(frozen['proposed_full_body']).parent,frozen,m)
expected=[v['run_id']for v in g.load(p/'native/plan.json')['queue']]
g.validate_completion(g.load(g.PREVIOUS_OUT/'primary/status.json'),g.load(g.PREVIOUS_OUT/'primary/terminal.json'),g.load(g.PREVIOUS_OUT/'exit.json'),ADMISSION,expected)
processes=g.previous_models_exited();lease=g.load(g.LEASE)
assert g.sha(g.LEASE)=='8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a'
holder=lease['holder'];actual=g.identity(holder['pid'])
assert actual['state']not in ['Z','X']and all(actual[k]==holder[k]for k in ['uid','command','start_ticks'])
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd'])
 assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and 'WRITE '+str(holder['pid'])in(proc/'fdinfo'/str(row['fd'])).read_text()
previous=g.load(g.PREVIOUS_OUT/'expanded-lease.json');uuids={row['index']:row['uuid']for row in previous['gpu']}
for row in lease['gpu']:assert uuids[row['index']]==row['uuid']
snapshot=g.gpu_snapshot();g.validate_gpu(snapshot,uuids)
stat=os.statvfs(p);assert stat.f_bavail*stat.f_frsize>64*1024**3
old=Path(OLD_COMMAND);assert g.sha(old)==OLD_COMMAND_SHA and old.with_suffix('.claimed').exists()
commands=g.LEASE.parent/'commands';assert not list(commands.glob(Path(COMMAND_NAME).stem+'*'))
assert all(q.with_suffix('.claimed').exists()for q in commands.glob('*.json'))
admissionfile=p/'previous-GUI-admission.json';g.save(admissionfile,ADMISSION)
command=commands/COMMAND_NAME
g.save(command,{'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'offline_launcher.py'),g.sha(admissionfile)],'script_sha256':g.sha(p/'offline_launcher.py')})
print(json.dumps({'time':time.time(),'command':str(command),'command_sha256':g.sha(command),
 'manifest_sha256':EXPECTED,'admission_sha256':g.sha(admissionfile),'linked_preserved_zero_call_parent':parent,
 'shared_authorized_maximum_calls':10,'previous_model_exits':processes,'fresh_exclusive_GPU_snapshot':snapshot,
 'condition_change':False,'new_GUI_Flash_scorer_calls':0,'old_failure_and_cost_not_erased':True}))
''')
    raw, op = remote('3090', code, 'submit-once-source-bound-zero-call-receipt-repair')
    result = json.loads(raw)
    save(PREP / 'submission.json', {'result': result, 'operation': str(op), 'GUI_recheck': gui,
        'GUI_operation': str(gui_op), 'source_sha256': sha(__file__), 'original_submission': str(PRIOR / 'submission.json'),
        'same_original_user_authorization_and_shared_ten_call_budget': True})
    print(json.dumps({'command': result['command'], 'manifest_sha256': result['manifest_sha256'],
        'previous_offline_calls': 0, 'remaining_authorized_maximum_calls': 10,
        'new_GUI_Flash_scorer_calls': 0, 'condition_change': False}))


if __name__ == '__main__':
    main()
