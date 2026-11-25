"""Compact read-only live snapshot; public candidates remain separated from outcomes."""
import json,subprocess,sys
from pathlib import Path
B=Path(__file__).resolve().parent
def run(name):
    p=subprocess.run([sys.executable,str(B/name)],capture_output=True,text=True,encoding='utf-8')
    if p.returncode:raise RuntimeError(p.stderr+p.stdout)
    return json.loads(p.stdout)
public=run('export_strict_price_public_candidates_retry1.py')
state=run('inspect_strict_price_fullgui_retry1.py');counts=state['attempts'][0]['counts']if state['attempts']else{}
print(json.dumps({'phase':state['status'].get('phase'),'step':state['status'].get('step'),'terminal':state['terminal'],'verified_actual_worker':state['actual_worker_verified'],
 'actor_candidates':counts.get('candidate',0),'judge_requests':counts.get('verifier_request',0),'judge_replies':counts.get('verifier_raw',0),
 'environment_actions':counts.get('action_executed',0),'recapture_requests':counts.get('recapture_requested',0),
 'new_candidates':public.get('new_rows',[]),'failures':state['failures']},ensure_ascii=True))
