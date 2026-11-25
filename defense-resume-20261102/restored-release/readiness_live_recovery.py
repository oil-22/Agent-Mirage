"""Two-step LIVE recovery diagnostic initialized from an explicitly replayed prefix.

Not a new natural full trajectory, not a formal outcome, never called a real recapture
of the old browser. The prefix is replayed by real GUI actions in a fresh context.
"""
import argparse,base64,copy,json,os,sys,time,traceback
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,digest,canonical
from defense.http_backend import RemoteQwen

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--gate',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
 a.root.mkdir(exist_ok=False,parents=True);log=Journal(a.root/'recovery');shots=a.root/'screenshots';shots.mkdir()
 def status(**kw):(a.root/'status.json').write_text(json.dumps(kw))
 marker=a.source/'runs/vwa--classifieds_112--blank_replace--joint/complete.json';pointer=json.loads(marker.read_text());source=Path(pointer['attempt'])
 assert digest((source/'complete.json').read_bytes())==pointer['sha256'];result=json.loads((source/'complete.json').read_text())
 assert result['outcome']=='blocked'and result['blocked_reason']=='observation_not_confirmed'
 events=[json.loads(l)for l in(source/'events.jsonl').read_text().splitlines()]
 actual=[e for e in events if e['kind']=='action_executed'];assert len(actual)==22
 observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
 last=next(e['data']['public']for e in reversed(events)if e['kind']=='observation'and e['data'].get('audience','actor')=='actor')
 manifest={'source_attempt':str(source),'source_events_sha256':digest((source/'events.jsonl').read_bytes()),
  'source_complete_sha256':pointer['sha256'],'replayed_executed_prefix':len(actual),'source_actor_calls':result['actor_calls'],
  'source_verifier_calls':result['verifier_calls'],'diagnostic_step_cap':2,'official_scoring':'not_run_diagnostic',
  'scope':'Fresh live browser with archived executed prefix and actual legal actor history. Not a new natural whole-task trajectory or formal result.'}
 (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
 base=Path('/data/researcher/vwa100-2026-10-09');sys.path[:0]=[str(base),str(base/'upstream/visualwebarena-main')]
 from run_reddit_internvl_smoke import parse,action,png
 from browser_env import ScriptBrowserEnv
 from browser_env.actions import create_page_focus_action
 template=json.loads((Path(__file__).parent/'native-vwa-request.json').read_text())
 env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
 model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
 c=Controller(model.judge,log,'joint',Limits(probe_current_targets=True,probe_target_alignment=True,full_completion_history=True,probe_completion=True,probe_history_reports=True,probe_observation_readiness=True))
 c.actor_calls=result['actor_calls'];c.verifier_calls=result['verifier_calls']
 for e in events:
  if e['kind']!='decision_accepted':continue
  accepted=e['data'];p=observations[accepted['observation_id']]
  ims=tuple(VisibleImage((source/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
  c.remember(PublicView(p['observation_id'],p['messages'],ims,p['recent_action'],p['execution_feedback'],p['observed_at']),accepted['candidate'])
 status(phase='replaying_actual_gui_prefix',actions=0)
 try:
  obs,info=env.reset(seed=20261011,options={'config_file':str(source/'official_config.json')});feedback=''
  for i,e in enumerate(actual,1):
   payload=e['data']['proposal']['payload'];native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
   if payload['type']=='wait':env.page.wait_for_timeout(1000)
   obs,ok,_,_,info=env.step(native);assert ok,info
   raw=png(obs);(shots/f'prefix-{i:03}.png').write_bytes(raw)
   log.append('prefix_action_replayed',{'source_event_seq':e['seq'],'payload':payload,'actual_capture_sha256':digest(raw)})
   feedback=json.dumps({'execution_returned':bool(ok),'error':info.get('fail_error',''),'result_state':'not confirmed by execution alone'})
  before=png(env._get_obs());(shots/'before-recovery.png').write_bytes(before)
  status(phase='waiting_reviewed_controls',replayed=len(actual))
  deadline=time.time()+1800
  while not a.gate.exists():
   if time.time()>deadline:raise RuntimeError('Bounded prerequisite deadline')
   time.sleep(2)
  gate=json.loads(a.gate.read_text());assert gate['phase']=='completed'and gate['passed'],gate
  messages=copy.deepcopy(last['messages']);history=messages[:-1];current=copy.deepcopy(messages[-1]);assert current['role']=='user'
  assert isinstance(current['content'],list)and sum(b.get('type')=='image_url'for b in current['content'])==1
  sequence=0;last_payload=actual[-1]['data']['proposal']['payload'];executed=0;accepted_rows=[]
  def public(raw):
   nonlocal sequence
   sequence+=1;user=copy.deepcopy(current)
   for block in user['content']:
    if block.get('type')=='image_url':block['image_url']={'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}
   return PublicView('live-recovery-'+str(sequence),copy.deepcopy(history)+[user],(VisibleImage(raw),),json.dumps(last_payload),feedback)
  for step in range(1,3):
   raw=png(env._get_obs());(shots/f'recovery-{step:03}-before.png').write_bytes(raw)
   def actor(v,corrections):
    body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=copy.deepcopy(v.messages);return model.actor(body)
   def parser(text):
    payload=parse(text)
    if payload['type']=='tab':assert 0<=int(payload['index'])<len(env.context.pages)
    else:action(payload)
    return {'name':payload['type'],'payload':payload,'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
   def recapture():return public(png(env._get_obs()))
   status(phase='live_recovery_decision',step=step,executed=executed)
   decision=c.decide(public(raw),actor,parser,recapture)
   if decision['status']!='accepted':raise RuntimeError('Recovery blocked: '+json.dumps(decision))
   payload=decision['proposal']['payload'];assert payload['type']!='stop','Unexpected terminal proposal; not a two-action recovery result'
   native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
   if payload['type']=='wait':env.page.wait_for_timeout(1000)
   obs,ok,_,_,info=env.step(native);assert ok,info
   feedback=json.dumps({'execution_returned':bool(ok),'error':info.get('fail_error',''),'result_state':'not confirmed by execution alone'})
   c.executed(decision,feedback);executed+=1;accepted_rows.append(decision)
   after=png(env._get_obs());(shots/f'recovery-{step:03}-after.png').write_bytes(after)
   if c.last_corrections:history.append({'role':'user','content':'Evidence verification correction retained: '+json.dumps(c.last_corrections,ensure_ascii=False)})
   task=next(b['text']for b in current['content']if b.get('text','').startswith('Task: '))
   history.extend([{'role':'user','content':task+'\nPrevious observation request.'},{'role':'assistant','content':decision['candidate']}]);last_payload=payload
  summary={'phase':'completed','passed':executed==2 and digest(before)!=digest(after),'actual_recovery_actions':executed,
   'decisions':accepted_rows,'new_actor_calls':c.actor_calls-result['actor_calls'],'new_verifier_calls':c.verifier_calls-result['verifier_calls'],
   'before_sha256':digest(before),'after_sha256':digest(after),'official_reward':None,'not_formal_completion':True,
   'scope':manifest['scope']+' Two actions and changed visible evidence only; not whole-task recovery.'}
  (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));status(phase='completed',passed=summary['passed'])
 except Exception:
  (a.root/'failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'not_completed':True},indent=2));status(phase='failed');raise
 finally:
  try:env.save_trace(a.root/'browser_trace.zip')
  finally:env.close()

if __name__=='__main__':main()
