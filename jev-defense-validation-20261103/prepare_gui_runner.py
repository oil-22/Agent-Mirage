"""Prepare a separate two-trajectory runner; never execute the old queue."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
release = base / 'release'
parent = release / 'run_vwa_pilot.py'
original = parent.read_text(encoding='utf-8')
text = original


def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new)


replace('from defense.http_backend import RemoteQwen',
        'from defense.http_backend import RemoteQwen\nfrom jev_cued_controller import from_config as cued_controller\nfrom validation_launch_contract import validate_launch_inputs')
start = text.index(' ap=argparse.ArgumentParser();')
end = text.index('\n a.root.mkdir', start)
text = text[:start] + ''' ap=argparse.ArgumentParser()
 for name in ['root','plan','token-file','runtime','native-task','actor-template','auxiliary-config','readiness']:
  ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--model-url',required=True);a=ap.parse_args()
 validate_launch_inputs(a)
 # Old optional queue/diagnostic modes are not exposed in this new runner.
 a.environment_preflight=False;a.priority_runs=[];a.only_runs=None;a.diagnostic_run=None;a.diagnostic_step_cap=None''' + text[end:]
replace("a.root.mkdir(parents=True,exist_ok=True)", "a.root.mkdir(parents=True,exist_ok=False)")
replace("assert len(queue)==20", "assert len(queue)==2 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue)")
start = text.index(' # Finite prerequisite wait,')
end = text.index(" from run_reddit_internvl_smoke", start)
text = text[:start] + ''' # Readiness was validated before creating the once-only experiment root.
 assert model.health()['phase']=='ready','Main model is not ready; no GUI started'
 base=a.runtime;source=base/'upstream'
 sys.path[:0]=[str(base/'native'),str(source)]
''' + text[end:]
replace("template=json.loads((a.plan.parent/'native-vwa-request.json').read_text())", "template=json.loads(a.actor_template.read_text())")
replace("original_config=base/'selected100-classifieds-reddit'/task['evaluation_config'];raw=original_config.read_bytes()", "original_config=a.native_task;raw=original_config.read_bytes()")
replace("controller=Controller(model.judge,log,item['arm'],Limits(", "controller=cued_controller(a.auxiliary_config,model.judge,log,item['arm'],Limits(")
replace("['run_vwa_pilot.py','defense/core.py','defense/prompts.py']", "['run_jev_vwa_validation.py','jev_cued_controller.py','validation_launch_contract.py','defense/core.py','defense/prompts.py']")
replace("log.append('defense_configuration',vars(controller.limits))", "log.append('defense_configuration',{'limits':vars(controller.limits),'policy':'jev-cued-judge-v1','auxiliary_calls_cap':60,'plan_sha256':digest(a.plan.read_bytes()),'readiness_sha256':digest(a.readiness.read_bytes())})")
replace("result['technical_status']='verifier_failure'", "result['auxiliary_calls']=controller.jev_auxiliary.calls\n   result['auxiliary_cap']=controller.jev_auxiliary.max_calls\n   result['technical_status']='verifier_failure'")
# New outer launcher must seal logs after exit; no terminal is retried in this worker.
target = release / 'run_jev_vwa_validation.py'
assert not target.exists()
ast.parse(text)
target.write_text(text, encoding='utf-8')
diff = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
           fromfile='original-run_vwa_pilot.py', tofile=target.name))
(base / 'gui-runner-diff.patch').write_text(diff, encoding='utf-8')
receipt = {'parent': str(parent), 'parent_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
           'new_runner_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'native_actor_parser_executor_history_injection_and_scoring_body': 'unchanged',
           'scope': 'Separate clean and stale_replace joint development trajectories only',
           'executed': False, 'still_requires_launch_ownership_and_terminal_auditor': True}
(base / 'gui-runner-staging.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
