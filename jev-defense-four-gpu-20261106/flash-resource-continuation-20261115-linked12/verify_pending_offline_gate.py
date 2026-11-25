"""One read-only real-state negative check: running GUI must refuse offline10."""
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha
from offline_followup_control import PREP, PACKAGE, REMOTE, OUTPUT, OLD_REMOTE, OLD_OUTPUT, COMMAND_NAME


def main():
    assert (PREP / 'stage-receipt.json').exists()
    assert not (PREP / 'pending-gate-check.json').exists()
    code = ('PACKAGE=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json'))
            + '\nOUTPUT=' + repr(OUTPUT) + '\nOLD_OUTPUT=' + repr(OLD_OUTPUT)
            + '\nOLD_PACKAGE=' + repr(OLD_REMOTE) + '\nCOMMAND_NAME=' + repr(COMMAND_NAME) + '\n' + r'''
import json,os,sys,time
from pathlib import Path
p=Path(PACKAGE);sys.path.insert(0,str(p));import offline_guard as g
assert os.getuid()==1033 and g.sha(p/'offline-manifest.json')==EXPECTED
m,plan=g.verify_package()
b=g.load(p/'aggregate-bindings.json');current=Path(b['continuation_output'])
status=g.load(current/'primary/status.json')
assert status['phase']!='completed'and status['done']<13,'The running-state negative is no longer applicable'
expected=[v['run_id']for v in g.load(p/'native/plan.json')['queue']]
try:
 g.validate_completion(g.load(g.PREVIOUS_OUT/'primary/status.json'),g.load(g.PREVIOUS_OUT/'primary/terminal.json'),g.load(g.PREVIOUS_OUT/'exit.json'),{},expected)
except (AssertionError,FileNotFoundError)as exc:
 if isinstance(exc,FileNotFoundError):
  assert exc.filename==str(current/'primary/terminal.json')and not(current/'primary/terminal.json').exists()
 rejected=True;refusal={'type':type(exc).__name__,'missing_file':getattr(exc,'filename',None)}
else:raise AssertionError('Actual still-running GUI was incorrectly admitted')
assert 'torch'not in sys.modules
assert not Path(OUTPUT).exists()and not Path(OLD_OUTPUT).exists()
assert not(p/'previous-GUI-admission.json').exists()and not(Path(OLD_PACKAGE)/'previous-GUI-admission.json').exists()
assert not list((g.LEASE.parent/'commands').glob(Path(COMMAND_NAME).stem+'*'))
print(json.dumps({'time':time.time(),'actual_continuation_status':status,
 'real_running_group_strictly_refused_by_staged_completion_guard':rejected,'refusal':refusal,
 'old_and_new_offline_output_and_shared_command_absent':True,'torch_imported':False,
 'new_model_GPU_GUI_calls':0,'positive_all29_admission_not_yet_exercised':True}))
''')
    raw, op = remote('3090', code, 'actual-running-GUI-negative-offline-admission-check')
    result = json.loads(raw)
    save(PREP / 'pending-gate-check.json', {'result': result, 'operation': str(op),
         'source_sha256': sha(Path(__file__)), 'time': time.time()})
    print(json.dumps(result))


if __name__ == '__main__':
    main()
