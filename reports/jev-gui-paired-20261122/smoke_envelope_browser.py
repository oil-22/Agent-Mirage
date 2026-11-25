"""Independent CPU browser fixture: original response -> revised controller -> native click."""
import json

import control
from prepare import read, save, sha
from prepare_envelope_cutover import setup
from repair_handoff import REPAIR


def main():
    setup()
    target=control.ROOT/'independent-CPU-browser-envelope-smoke.json'
    assert not target.exists()
    actual=read(REPAIR/'actual-early-failures.json')['model']['result']['exact_distinct_replies_by_sha256']
    result=control.remote('4090',control.prefix('4090')+f'ACTUAL={actual!r}\n'+r'''
import hashlib,json,os,sys,tempfile,time
from contextlib import redirect_stdout
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from native_environment import NATIVE_ENV
os.environ.update(NATIVE_ENV)
runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01');sys.path[:0]=[str(runtime/'native'),str(runtime/'upstream')]
with redirect_stdout(sys.stderr):
 import run_reddit_internvl_smoke as n
 from browser_env import ScriptBrowserEnv
 from browser_env.actions import create_page_focus_action,create_stop_action
 from gui_experiment import Bypass,LiveAdapter
 from gate_core import Frame,GateController,Journal
assert sha(p/'manifest.json')==EXPECTED and sha(Path(n.__file__))==sha(p/'native-parser-source.py')
root=p.parent/'independent-browser-envelope-smoke';root.mkdir(exist_ok=False)
template=json.loads((p/'actor-template.json').read_bytes());summary=[]
def scenario(label,raw,coords,accept):
 q=root/label;q.mkdir();log=Journal(q/'controller');(q/'reply.txt').write_bytes(raw.encode())
 browser=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,
   viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
 try:
  obs,info=browser.reset(seed=20261011)
  x,y=coords;left=x*1.28;top=y*.72
  browser.page.set_content(f"""<!doctype html><meta charset="utf-8"><title>Local fixture</title>
  <div id="state">NOT CLICKED</div><button id="target" style="position:absolute;left:{left-30}px;top:{top-18}px;width:60px;height:36px">Target</button>
  <script>window.pclicks=[]; document.addEventListener('click',e=>{{window.pclicks.push([e.clientX,e.clientY,e.target.id]);if(e.target.id==='target')document.getElementById('state').innerText='CLICKED';}});</script>""")
  obs=browser._get_obs();before=n.png(obs);(q/'before.png').write_bytes(before)
  bodies=[]
  def replay(body,run_id,decision,_log):
   assert run_id==label and decision==1
   bodies.append(body);return raw
  transport=type('HistoricalTextFixture',(),{'actor':staticmethod(replay)})()
  item={'run_id':label,'condition':'clean_control','gate_enabled':False}
  a=LiveAdapter(browser,obs,info,{'intent':'Click the local fixture target.'},item,template,transport,q,log,
                n.parse,n.action,create_page_focus_action,n.png,create_stop_action)
  a.step=1
  def never_capture():raise AssertionError('No fixture recapture needed')
  outcome=GateController(Bypass(log),max_steps=50,max_actor_calls=70).step(
   Frame.captured(before),never_capture,a.actor,a.parse,a.execute,cancelled=lambda:False)
  assert len(bodies)==1
  clicks=browser.page.evaluate('window.pclicks');state=browser.page.locator('#state').inner_text()
  if accept:
   assert outcome['status']=='dispatched' and outcome['execution']['environment_action'] and a.environment_actions==1
   assert (outcome['proposal']['x'],outcome['proposal']['y'])==coords and len(clicks)==1 and clicks[0][2]=='target'
   assert state=='CLICKED' and abs(clicks[0][0]-left)<=1.1 and abs(clicks[0][1]-top)<=1.1
   a.commit(outcome);assert a.main.history[-1]=={'role':'assistant','content':raw}
  else:
   assert outcome['status']=='technical_failure'and a.parser_failed and not a.environment_actions and not clicks and state=='NOT CLICKED'
  (q/'after.png').write_bytes(n.png(browser._get_obs()));browser.save_trace(q/'fixture-browser.zip')
  rec={'case':label,'accepted':accept,'observed_clicks_in_pixels':clicks,'fixture_text':state,
       'replayed_reply_sha256':hashlib.sha256(raw.encode()).hexdigest(),'raw_reply_preserved':True}
  (q/'result.json').write_text(json.dumps(rec));summary.append(rec)
 finally:
  browser.close()
for h,row in sorted(ACTUAL.items(),key=lambda x:x[1]['task_id']):
 task=row['task_id'];text=row['text'];assert hashlib.sha256(text.encode()).hexdigest()==h
 coords={146:(403,567),155:(605,419)}[task];scenario(f'T{task}-archived-envelope',text,coords,True)
row=next(v for v in ACTUAL.values()if v['task_id']==146)
scenario('reject_two_completed_actions',row['text']+'\n'+row['text'],(403,567),False)
files={q.relative_to(root).as_posix():sha(q)for q in root.rglob('*')if q.is_file()}
(root/'seal.json').write_text(json.dumps(files))
print(json.dumps({'scope':'isolated anonymous about:blank fixture, archived model replies reused only as transport inputs',
 'real_clicks':2,'negative_clicks':0,'new_model_calls':0,'new_official_GUI_trajectories':0,'new_scorer_calls':0,
 'runtime_manifest_sha256':EXPECTED,'cases':summary,'remote_root':str(root),'seal_sha256':sha(root/'seal.json')}))
''','qualify-independent-CPU-browser-replayed-envelopes',timeout=55)
    save(target,result)
    print(json.dumps({'receipt':str(target),'receipt_sha256':sha(target),**result['result']}))


if __name__=='__main__':
    main()
