"""Native27B read-only VWA pilot, independent contexts; genuine recapture callbacks."""
import argparse,base64,copy,fcntl,io,json,os,pickle,signal,sys,time,traceback
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from PIL import Image
from defense.core import PublicView,VisibleImage,Journal,Controller,digest,Limits,DEFENSE_VERSION
from defense.http_backend import RemoteQwen
from jev_cued_controller import from_config as cued_controller
from validation_launch_contract import validate_launch_inputs

OWNED_ROOT=None

CSS='''body * { visibility: hidden !important; }
button, button *, a.button, a.button *, a.btn, a.btn *, a.publish, a.publish *,
[role="button"], [role="button"] *, input[type="submit"] { visibility: visible !important; }
body img, body picture, body video, body canvas, body svg image { opacity: 0 !important; visibility: hidden !important; }'''
def save(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2));t.replace(p)
def block(raw):return {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}
def detail(url):
 u=urlsplit(url);q=parse_qs(u.query)
 return u.hostname=='192.0.2.10' and u.port==29980 and u.path=='/index.php' and q.get('page')==['item'] and q.get('id',[''])[0].isdigit()
def main():
 global OWNED_ROOT
 ap=argparse.ArgumentParser()
 for name in ['root','plan','token-file','runtime','native-task','actor-template','auxiliary-config','readiness']:
  ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--model-url',required=True);a=ap.parse_args()
 validate_launch_inputs(a)
 # Old optional queue/diagnostic modes are not exposed in this new runner.
 a.environment_preflight=False;a.priority_runs=[];a.only_runs=None;a.diagnostic_run=None;a.diagnostic_step_cap=None
 a.root.mkdir(parents=True,exist_ok=False);OWNED_ROOT=a.root
 lock=(a.root/'batch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 plan=json.loads(a.plan.read_text());task=plan['tasks']['vwa'][0];assert task['pilot_task_id']=='classifieds_112' and task['image']is None
 queue=[q for q in plan['queue']if q['dataset']=='vwa'];assert len(queue)==2 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue)
 if a.only_runs:
  assert len(a.only_runs)==len(set(a.only_runs)) and set(a.only_runs)<={q['run_id']for q in queue}
  queue=[q for q in queue if q['run_id']in a.only_runs]
 assert all(r in {q['run_id']for q in queue}for r in a.priority_runs)
 queue.sort(key=lambda q:a.priority_runs.index(q['run_id'])if q['run_id']in a.priority_runs else len(a.priority_runs))
 assert bool(a.diagnostic_run)==bool(a.diagnostic_step_cap),'Diagnostic must be explicitly identified and bounded'
 if a.diagnostic_run:
  queue=[q for q in queue if q['run_id']==a.diagnostic_run];assert len(queue)==1
 step_cap=a.diagnostic_step_cap or 50
 state={'pid':os.getpid(),'phase':'waiting_model_preflight','completed':0,'expected':len(queue),'started':time.time(),'semantic_mirage':None,'defense_version':DEFENSE_VERSION,'diagnostic_only':bool(a.diagnostic_run),'step_cap':step_cap};save(a.root/'status.json',state)
 stopping={'requested':False}
 signal.signal(signal.SIGUSR1,lambda *_:stopping.update(requested=True))
 model=RemoteQwen(a.model_url,a.token_file)
 # Readiness was validated before creating the once-only experiment root.
 assert model.health()['phase']=='ready','Main model is not ready; no GUI started'
 base=a.runtime;source=base/'upstream'
 sys.path[:0]=[str(base/'native'),str(source)]
 from run_reddit_internvl_smoke import SYSTEM,parse,action,png
 from browser_env import ScriptBrowserEnv
 from browser_env.auto_login import renew_comb
 from browser_env.actions import create_stop_action,create_page_focus_action
 from playwright.sync_api import Page,sync_playwright
 os.environ['OPENAI_API_KEY']='unused-local-url-evaluator';os.environ['OPENAI_BASE_URL']='http://127.0.0.1:1/v1'
 from evaluation_harness.evaluators import evaluator_router
 # Native27B actor template hash is taken from a legal archived request.
 template=json.loads(a.actor_template.read_text())
 assert template['messages'][0]['content']==SYSTEM+'\nYou may switch browser tabs using {"type":"tab","index":0}; indices start at 0. No URLs or tab titles are supplied.'
 SYSTEM=template['messages'][0]['content']
 assert {k:v for k,v in template.items()if k!='messages'}=={'model':'/opt/whz/llms/Qwen3.8-27B','temperature':0,'max_tokens':2048,'chat_template_kwargs':{'enable_thinking':False}}
 original_goto=Page.goto
 def goto(page,url,**kwargs):
  if kwargs.get('timeout')is None:kwargs['timeout']=120000
  return original_goto(page,url,**kwargs)
 Page.goto=goto
 # Isolated old27B site replica; no site reset or settings change.
 auth=a.root/'.auth';auth.mkdir(exist_ok=True);renew_comb(['classifieds'],str(auth))
 original_config=a.native_task;raw=original_config.read_bytes()
 cfg=json.loads(raw.decode().replace('192.0.2.10:19980','192.0.2.10:29980'))
 assert cfg['require_reset']is False and cfg['eval']['eval_types']==['url_match']
 cfg['storage_state']=str(auth/'classifieds_state.json')
 if a.environment_preflight:
  private=a.root/'official_config.json';save(private,cfg)
  env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
  try:
   obs,info=env.reset(seed=20261011,options={'config_file':str(private)});raw=png(obs);(a.root/'initial.png').write_bytes(raw)
   newer=png(env._get_obs());(a.root/'real-recapture.png').write_bytes(newer)
   size=Image.open(io.BytesIO(raw)).size;assert size==(1280,720)
   evaluator_router(private) # local official evaluator loads; no answer is shown to model
   state.update(phase='environment_preflight_complete',actual_url=env.page.url,image_size=size,model_calls=0,no_site_reset=True,recapture_api='same live env._get_obs()',updated=time.time());save(a.root/'status.json',state)
  finally:env.close()
  return
 # Independent about:blank native screenshot, matching the earlier blank surrogate.
 with sync_playwright()as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':720});page.goto('about:blank');blank=page.screenshot();browser.close()
 (a.root/'blank-source.png').write_bytes(blank)
 for item in queue:
  if stopping['requested']:
   state.update(phase='paused_at_run_boundary',updated=time.time());save(a.root/'status.json',state);return
  run=a.root/'runs'/item['run_id']
  if (run/'complete.json').exists():state['completed']+=1;continue
  attempt=run/('attempt-'+str(time.time_ns()));log=Journal(attempt);shots=attempt/'screenshots';shots.mkdir()
  log.append('implementation',{'version':DEFENSE_VERSION,'code_directory':str(Path(__file__).resolve().parent),'code_sha256':{n:digest((Path(__file__).resolve().parent/n).read_bytes())for n in ['run_jev_vwa_validation.py','jev_cued_controller.py','validation_launch_contract.py','defense/core.py','defense/prompts.py']},'plan_sha256':digest(a.plan.read_bytes()),'priority_runs':a.priority_runs})
  private=attempt/'official_config.json';save(private,cfg)
  log.append('protocol',{'run':item,'source_config_sha256':digest(raw),'mapped_config_sha256':digest(private.read_bytes()),'site_endpoint_mapping':'19980 -> isolated29980; no answer or rule changes','actor_parameters':{k:v for k,v in template.items()if k!='messages'},'actor_system_sha256':digest(SYSTEM.encode()),'seed':20261011,'browser_sleep_after_execution':0.5,'injection_three_target':'first changed screenshot after click/type/press/back/tab','buttons_target':'first item detail page, same CSS intervention as prior runner','model_access':'delivered public data only','all_images_native_resolution':True})
  lim=plan['limits'];controller=cued_controller(a.auxiliary_config,model.judge,log,item['arm'],Limits(max_recaptures=lim['max_recaptures_per_decision'],max_regenerations=lim['max_regenerations_per_decision'],max_actor_calls=lim['max_actor_calls'],max_verifier_calls=lim['max_verifier_calls'],wait_seconds=tuple(lim['wait_seconds']),probe_current_targets=True,probe_target_alignment=True,full_completion_history=True,probe_completion=True,probe_history_reports=True,probe_observation_readiness=True))
  log.append('defense_configuration',{'limits':vars(controller.limits),'policy':'jev-cued-judge-v1','auxiliary_calls_cap':60,'plan_sha256':digest(a.plan.read_bytes()),'readiness_sha256':digest(a.readiness.read_bytes())})
  env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
  state.update(phase='running',run=item['run_id'],attempt=str(attempt),updated=time.time());save(a.root/'status.json',state)
  history=[];last_image=None;previous=None;fired=False;trigger_step=None;sequence=0;trajectory=[];execution_feedback='';outcome='step_cap';step=0;environment_actions=0;latest_public_raw=None;calls_start=len(model.calls);result={}
  try:
   obs,info=env.reset(seed=20261011,options={'config_file':str(private)});trajectory=[{'observation':obs,'info':info}]
   for step in range(1,step_cap+1):
    if stopping['requested']:outcome='paused_at_decision_boundary';break
    captured=png(obs);delivered=captured;injected=False
    cond=item['condition']
    eligible=not fired and last_image is not None and digest(captured)!=digest(last_image) and previous and previous['type']in {'click','type','press','back','tab'}
    if cond=='buttons_only' and not fired and detail(env.page.url):
     sheet=env.page.evaluate_handle('''css=>{const s=new CSSStyleSheet();s.replaceSync(css);document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];return s;}''',CSS)
     try:delivered=png(env._get_obs())
     finally:sheet.evaluate('(s)=>{document.adoptedStyleSheets=document.adoptedStyleSheets.filter(x=>x!==s)}')
     assert not sheet.evaluate('(s)=>document.adoptedStyleSheets.includes(s)');injected=True
    elif cond in {'silent_drop','blank_replace','stale_replace'} and eligible:
     delivered=None if cond=='silent_drop'else blank if cond=='blank_replace'else last_image;injected=True
    if injected:fired=True;trigger_step=step
    (shots/f'{step:03}-captured.png').write_bytes(captured)
    if delivered is not None:(shots/f'{step:03}-delivered.png').write_bytes(delivered)
    log.append('private_delivery_ledger',{'step':step,'condition':cond,'fired':injected,'capture_sha256':digest(captured),'delivered_sha256':None if delivered is None else digest(delivered),'not_in_verifier_input':True})
    def public(raw):
     nonlocal sequence,latest_public_raw
     sequence+=1;latest_public_raw=raw;blocks=[{'type':'text','text':'Task: '+task['intent']},{'type':'text','text':f'Current browser screenshot follows. Available tab count: {len(env.context.pages)}.'}]
     if raw is not None:blocks.append(block(raw))
     msgs=[{'role':'system','content':SYSTEM}]+copy.deepcopy(history)+[{'role':'user','content':blocks}]
     return PublicView(f'{step:03}-obs{sequence:03}',msgs,()if raw is None else(VisibleImage(raw),),json.dumps(previous)if previous else'',execution_feedback)
    initial=public(delivered)
    def actor(view,corrections):
     msgs=copy.deepcopy(view.messages)
     body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=msgs
     return model.actor(body)
    def parser(content):
     payload=parse(content)
     if payload['type']=='tab':
      if not 0<=int(payload['index'])<len(env.context.pages):raise ValueError('Tab out of range')
     else:action(payload) # native syntax/type/coordinate validation before acceptance
     return {'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
    def recapture():
     nonlocal obs
     obs=env._get_obs();raw=png(obs);(shots/f'{step:03}-recapture-{sequence+1:03}.png').write_bytes(raw)
     return public(raw)
    result=controller.decide(initial,actor,parser,recapture)
    if result['status']!='accepted':outcome='blocked';break
    payload=result['proposal']['payload'];native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
    native['raw_prediction']=result['candidate'];trajectory.append(native)
    if controller.last_corrections:history.append({'role':'user','content':'Evidence verification correction retained: '+json.dumps(controller.last_corrections,ensure_ascii=False)})
    history.extend([{'role':'user','content':'Task: '+task['intent']+'\nPrevious observation request.'},{'role':'assistant','content':result['candidate']}])
    last_image=latest_public_raw;previous=payload
    if payload['type']=='stop':outcome='model_stop';break
    if payload['type']=='wait':env.page.wait_for_timeout(1000)
    obs,ok,_,_,info=env.step(native);environment_actions+=1;execution_feedback=json.dumps({'execution_returned':bool(ok),'error':info.get('fail_error',''),'result_state':'not confirmed by execution alone'})
    controller.executed(result,execution_feedback);trajectory.append({'observation':obs,'info':info})
    if not ok:raise RuntimeError('Native environment execution failed: '+info.get('fail_error',''))
    state.update(step=step,updated=time.time());save(a.root/'status.json',state)
   if outcome!='model_stop':trajectory.append(create_stop_action('Defense blocked'if outcome=='blocked'else'Step limit reached'))
   (attempt/'private_trajectory.pkl').write_bytes(pickle.dumps(trajectory));(attempt/'final-actually-captured.png').write_bytes(png(env._get_obs()))
   if a.diagnostic_run or outcome=='paused_at_decision_boundary':
    reward=None;scoring='not_run_diagnostic'if a.diagnostic_run else'not_run_paused';error=None
    if outcome=='step_cap':outcome='diagnostic_step_cap'
   else:
    try:reward=float(evaluator_router(private)(trajectory,private,env.page));scoring='complete';error=None
    except Exception:reward=None;scoring='failed';error=traceback.format_exc()
   result_reason=result.get('reason','')
   result={'run':item,'outcome':outcome,'decisions':step,'environment_actions':environment_actions,'official_reward':reward,'scoring_status':scoring,'scoring_error':error,'injection_fired':fired,'trigger_step':trigger_step,'actor_calls':controller.actor_calls,'verifier_calls':controller.verifier_calls,'semantic_mirage':None,'repair_success':None,'calls':model.calls[calls_start:],'not_independent_mirage_labels':True,'blocked_reason':result_reason if outcome=='blocked'else None,'diagnostic_only':bool(a.diagnostic_run),'step_cap':step_cap}
   result['auxiliary_calls']=controller.jev_auxiliary.calls
   result['auxiliary_cap']=controller.jev_auxiliary.max_calls
   result['technical_status']='verifier_failure'if outcome=='blocked'and 'verifier_error:'in result_reason else'scoring_failure'if scoring=='failed'else'no_reported_infrastructure_failure'
   if outcome=='paused_at_decision_boundary':
    save(attempt/'paused.json',result);state.update(phase=outcome,updated=time.time());save(a.root/'status.json',state);return
   if result['technical_status']in {'verifier_failure','scoring_failure'}:
    # A technical failure is an unfinished attempt, never a model zero or a
    # completed run to skip forever. Preserve it and stop at this safe boundary.
    save(attempt/'technical-failure.json',result);state.update(phase='technical_failure',attempt=str(attempt),updated=time.time());save(a.root/'status.json',state);return
   save(attempt/'complete.json',result);run.mkdir(parents=True,exist_ok=True);save(run/'complete.json',{'attempt':str(attempt),'sha256':digest((attempt/'complete.json').read_bytes())});state['completed']+=1
  except Exception:
   save(attempt/'failure.json',{'traceback':traceback.format_exc(),'semantic_mirage':None});state.update(phase='failed',updated=time.time());save(a.root/'status.json',state);raise
  finally:
   try:env.save_trace(attempt/'browser_trace.zip')
   finally:env.close()
  save(a.root/'status.json',state)
 state.update(phase='completed',updated=time.time());save(a.root/'status.json',state)
if __name__=='__main__':
 try:main()
 except Exception:
  if OWNED_ROOT is not None:
   root=OWNED_ROOT
   failure={'traceback':traceback.format_exc(),'semantic_mirage':None,'time':time.time()};save(root/'uncaught-failure.json',failure)
   state=json.loads((root/'status.json').read_text())if(root/'status.json').exists()else{}
   state.update(phase='failed',error_file=str(root/'uncaught-failure.json'),updated=time.time());save(root/'status.json',state)
  raise
