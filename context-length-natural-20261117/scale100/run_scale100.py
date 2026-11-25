"""Natural-context pilot: clean trajectories, isolated decisions, matched-prefix continuations.

No defense is enabled. Snapshot support is unavailable: replayed browser prefixes
are explicitly labelled and require matching visible state before continuation.
Semantic eligibility and Agent-Mirage labels remain pending human audit.
"""
import base64, copy, fcntl, hashlib, io, json, os, signal, sys, time, traceback
from pathlib import Path
import requests
from PIL import Image

P=Path(__file__).resolve().parent
from native_environment import NATIVE_ENV
os.environ.update(NATIVE_ENV)
NATIVE=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
sys.path[:0]=[str(NATIVE/'native'),str(NATIVE/'upstream')]
import run_reddit_internvl_smoke as native
from browser_env import ScriptBrowserEnv
from browser_env.auto_login import renew_comb
from browser_env.actions import create_page_focus_action, create_stop_action
from evaluation_harness.evaluators import evaluator_router
from playwright.sync_api import Page

R=P/'gui-output'
CFG=json.loads((P/'config.json').read_text())
TEMPLATE=json.loads((P/'actor-template.json').read_text())
TOKEN=(P/'service.token').read_text().strip()
URL='http://192.0.2.11:'+str(CFG['service_port'])
STOP=False
CALLS=0
CSS='''body * { visibility: hidden !important; }
button, button *, a.button, a.button *, a.btn, a.btn *, a.publish, a.publish *,
[role="button"], [role="button"] *, input[type="submit"] { visibility: visible !important; }
body img, body picture, body video, body canvas, body svg image { opacity: 0 !important; visibility: hidden !important; }'''

def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(p)
def state(**v):save(R/'status.json',{'time':time.time(),'model_calls':CALLS,**v})
def capture(env):return env.page.screenshot(type='png',caret='hide')
def stopping():return STOP or (P/'STOP').exists()
def rpc(path,payload):
    r=requests.post(URL+path,json=payload,headers={'Authorization':'Bearer '+TOKEN},timeout=1800)
    if r.status_code!=200:raise RuntimeError('Model service '+str(r.status_code)+': '+r.text[:2500])
    return r.json()
def generate(body,meta):
    global CALLS
    if stopping():raise InterruptedError('Manual stop')
    if CALLS>=CFG['max_model_calls']:raise RuntimeError('Natural batch call budget reached')
    CALLS+=1
    out=rpc('/generate',dict(body=body,meta=meta))
    if not out['natural_EOS']:raise ValueError('Generation reached cap without EOS; not a semantic event')
    return out
def imgblock(raw):return dict(type='image_url',image_url=dict(url='data:image/png;base64,'+base64.b64encode(raw).decode()))
def body_for(history,task,env,feedback,raw):
    blocks=[dict(type='text',text='Task: '+task['intent']),dict(type='text',text=f'Current browser screenshot follows. Available tab count: {len(env.context.pages)}.')]
    if feedback:blocks.append(dict(type='text',text='Previous native execution feedback (execution alone does not confirm the visible result): '+feedback))
    if raw is not None:blocks.append(imgblock(raw))
    body={k:copy.deepcopy(v) for k,v in TEMPLATE.items() if k!='messages'}
    reference_prefix=[]
    if not history and task.get('reference_image_paths'):
        reference_blocks=[dict(type='text',text='Task reference image(s). Use these to interpret the task; they are not current browser observations.')]
        reference_blocks.extend(imgblock((P/rel).read_bytes()) for rel in task['reference_image_paths'])
        reference_prefix=[dict(role='user',content=reference_blocks)]
    body['messages']=[copy.deepcopy(TEMPLATE['messages'][0])]+reference_prefix+copy.deepcopy(history)+[dict(role='user',content=blocks)]
    return body
def replace_current(body,raw):
    b=copy.deepcopy(body);b['messages'][-1]['content']=[x for x in b['messages'][-1]['content'] if x['type']!='image_url']
    if raw is not None:b['messages'][-1]['content'].append(imgblock(raw))
    return b
def fingerprint(env,raw):
    return dict(image_sha256=sha(raw),url=env.page.url,tab_urls=[p.url for p in env.context.pages],
        page_state=env.page.evaluate('''()=>({scrollX,scrollY,focusTag:document.activeElement?.tagName,focusId:document.activeElement?.id,focusValue:document.activeElement?.value??null})'''))
def new_env(private):
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,
        viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    obs,info=env.reset(seed=20261011,options={'config_file':str(private)})
    return env,obs,info
def execute(env,payload,reply):
    if payload['type']=='tab':
        assert 0<=int(payload['index'])<len(env.context.pages)
        action=create_page_focus_action(int(payload['index']))
    else:action=native.action(payload)
    action['raw_prediction']=reply
    if payload['type']=='stop':return action,None,None,''
    if payload['type']=='wait':env.page.wait_for_timeout(1000)
    obs,ok,_,_,info=env.step(action)
    feedback=json.dumps(dict(execution_returned=bool(ok),error=info.get('fail_error',''),result_state='not confirmed by execution alone'))
    if not ok:raise RuntimeError('Environment execution failure: '+info.get('fail_error',''))
    return action,obs,info,feedback
def controls_image(env,raw):
    # Rectangles are evaluator-side mask geometry, never delivered as DOM/text to the actor.
    rects=env.page.locator('button, a.button, a.btn, a.publish, [role="button"], input[type="submit"]').evaluate_all('''els=>els.filter(e=>{const s=getComputedStyle(e);return s.visibility!=="hidden"&&s.display!=="none"&&s.opacity!=="0"}).map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.right,r.bottom]})''')
    image=Image.open(io.BytesIO(raw)).convert('RGB');masked=Image.new('RGB',image.size,'white')
    import math
    clipped=[]
    for x,y,right,bottom in rects:
        box=(max(0,math.floor(x)),max(0,math.floor(y)),min(image.width,math.ceil(right)),min(image.height,math.ceil(bottom)))
        if box[2]>box[0] and box[3]>box[1]:masked.paste(image.crop(box),(box[0],box[1]));clipped.append(box)
    out=io.BytesIO();masked.save(out,format='PNG')
    return out.getvalue(),clipped
def score(env,private,trajectory):
    return float(evaluator_router(private)(trajectory,private,env.page))
def close_env(env,folder):
    try:env.save_trace(folder/'browser_trace.zip')
    finally:env.close()

def collect_clean(task,private,folder):
    folder.mkdir(parents=True);env,obs,info=new_env(private)
    history=[];actions=[];frames=[];checkpoints=[];feedback='';seen=set();outcome='step_cap'
    trajectory=[dict(observation=obs,info=info)]
    try:
        for step in range(1,CFG['max_steps']+1):
            if stopping():raise InterruptedError('Manual stop')
            raw=capture(env);(folder/f'{step:03}-observed.png').write_bytes(raw)
            body=body_for(history,task,env,feedback,raw)
            counts=rpc('/count',dict(body=body));length=counts['input_tokens']
            state(phase='clean_trajectory',task=task['task_id'],step=step,input_tokens=length,covered_bins=sorted(seen))
            for target in CFG['bins']:
                if target in seen or not target*.9<=length<=target*1.1:continue
                # Candidates are not labelled as valid Mirage events before evidence review.
                cp=folder/f'checkpoint-{target}';cp.mkdir()
                previous=next((f for f in reversed(frames) if f!=raw),None)
                (cp/'normal.png').write_bytes(raw)
                if previous is not None:(cp/'stale.png').write_bytes(previous)
                white=Image.new('RGB',Image.open(io.BytesIO(raw)).size,'white');white.save(cp/'blank.png')
                masked,rects=controls_image(env,raw);(cp/'controls.png').write_bytes(masked)
                save(cp/'PRIVATE-mask-geometry.json',dict(method='pixel-preserving control rectangles; page not modified',rectangles=rects,not_actor_input=True))
                save(cp/'body.json',body);save(cp/'prefix-actions.json',actions)
                record=dict(task=task['task_id'],bin=target,step=step,normal_input=counts,
                    fingerprint=fingerprint(env,raw),previous_distinct_image_available=previous is not None,
                    control_mask_changes_image=masked!=raw,visible_control_rectangles=len(rects),semantic_evidence_eligibility='pending_audit',
                    prior_Mirage_free_prefix='pending_audit',snapshot_type='browser action prefix replay, no full environment snapshot')
                save(cp/'checkpoint.json',record);checkpoints.append(cp);seen.add(target)
                # Decision replays occur while the exact original live state is still present.
                for condition,file in [('silent_drop',None),('blank_replace','blank.png'),('stale_replace','stale.png'),('buttons_only','controls.png')]:
                    if condition=='buttons_only' and not rects:
                        save(cp/(condition+'-skip.json'),dict(reason='No visible control regions; do not equate white image to controls-only'));continue
                    if file and not(cp/file).exists():
                        save(cp/(condition+'-skip.json'),dict(reason='No distinct historical image'));continue
                    delivered=(cp/file).read_bytes() if file else None
                    changed=replace_current(body,delivered)
                    state(phase='isolated_injection',task=task['task_id'],step=step,bin=target,condition=condition)
                    answer=generate(changed,dict(task=task['task_id'],stage='isolated_decision',bin=target,condition=condition,step=step))
                    try:answer['parsed_action']=native.parse(answer['text'])
                    except Exception:answer['parse_error']=traceback.format_exc()
                    save(cp/(condition+'-decision.json'),answer)
                save(cp/'post-probe-state.json',fingerprint(env,capture(env)))
                if json.loads((cp/'post-probe-state.json').read_text())!=record['fingerprint']:
                    save(cp/'original-state-drift.json',dict(reason='Live state drift during isolated probes; continue baseline from fresh observation; discard checkpoint for matched continuation'))
                    obs=env._get_obs();raw=capture(env);body=body_for(history,task,env,feedback,raw)
            # Preserve the screenshot actually delivered, including a fresh capture
            # after live-state drift during probes; keep the first capture too.
            actual_image=folder/f'{step:03}-observed.png'
            if actual_image.read_bytes()!=raw:
                actual_image=folder/f'{step:03}-delivered.png';actual_image.write_bytes(raw)
            answer=generate(body,dict(task=task['task_id'],stage='clean_control',step=step))
            save(folder/f'{step:03}-response.json',answer)
            save(folder/f'{step:03}-input-manifest.json',dict(current_image_path=str(actual_image),
                current_image_sha256=sha(raw),input_tokens=answer['input_tokens'],
                input_ids_sha256=answer['input_ids_sha256'],images=answer['images'],
                model_receipt=answer['receipt'],normal_history_only=True))
            try:payload=native.parse(answer['text'])
            except Exception:outcome='native_parse_failure';break
            record=dict(step=step,payload=payload,reply=answer['text'])
            save(folder/f'{step:03}-action.json',record)
            try:a,nextobs,nextinfo,feedback=execute(env,payload,answer['text'])
            except (ValueError,AssertionError,KeyError):outcome='native_action_contract_failure';break
            trajectory.append(a);actions.append(record);frames.append(raw)
            history=copy.deepcopy(body['messages'][1:])+[dict(role='assistant',content=answer['text'])]
            if payload['type']=='stop':outcome='model_stop';break
            obs,info=nextobs,nextinfo;trajectory.append(dict(observation=obs,info=info))
        if outcome!='model_stop':trajectory.append(create_stop_action('Experiment stopped: '+outcome))
        terminal=dict(outcome=outcome,steps=step,reward=score(env,private,trajectory),covered_bins=sorted(seen),
            uncovered_bins=[x for x in CFG['bins'] if x not in seen],checkpoints=[str(p) for p in checkpoints],semantic_labels='pending_audit')
        save(folder/'terminal.json',terminal)
    finally:close_env(env,folder)
    return checkpoints

def continue_branch(task,private,cp,condition,folder):
    folder.mkdir(parents=True)
    record=json.loads((cp/'checkpoint.json').read_text());original=json.loads((cp/'body.json').read_text())
    decision_path=cp/(condition+'-decision.json')
    if not decision_path.exists() or (cp/'original-state-drift.json').exists():
        save(folder/'terminal.json',dict(outcome='unavailable_checkpoint',not_semantic_failure=True));return
    env,obs,info=new_env(private);trajectory=[dict(observation=obs,info=info)]
    prefix=json.loads((cp/'prefix-actions.json').read_text());feedback='';outcome='step_cap'
    try:
        for r in prefix:
            a,obs,info,feedback=execute(env,r['payload'],r['reply']);trajectory.extend([a,dict(observation=obs,info=info)])
        actual=fingerprint(env,capture(env));save(folder/'replayed-state.json',actual)
        if actual!=record['fingerprint']:
            save(folder/'terminal.json',dict(outcome='prefix_state_mismatch',not_semantic_failure=True,
                 expected=record['fingerprint'],actual=actual,model_calls=0));return
        save(folder/'pairing.json',dict(visible_state_matched=True,full_environment_snapshot=False,checkpoint=str(cp),
            history_reused_exactly=True,read_only_navigation_tasks=True))
        file={'silent_drop':None,'blank_replace':'blank.png','stale_replace':'stale.png','buttons_only':'controls.png'}[condition]
        delivered=(cp/file).read_bytes() if file else None
        body=replace_current(original,delivered);history=[]
        for step in range(record['step'],CFG['max_steps']+1):
            if stopping():raise InterruptedError('Manual stop')
            state(phase='branch_continuation',task=task['task_id'],bin=record['bin'],condition=condition,step=step)
            if step==record['step']:
                answer=json.loads(decision_path.read_text())
                save(folder/'initial-decision-reuse.json',dict(source=str(decision_path),receipt=answer['receipt'],
                    no_second_generation=True,same_input_and_matched_visible_state=True))
            else:
                raw=capture(env);(folder/f'{step:03}-normal-observation.png').write_bytes(raw)
                body=body_for(history,task,env,feedback,raw)
                answer=generate(body,dict(task=task['task_id'],stage='branch_continuation',bin=record['bin'],condition=condition,step=step))
            save(folder/f'{step:03}-response.json',answer)
            try:payload=native.parse(answer['text'])
            except Exception:outcome='native_parse_failure';break
            save(folder/f'{step:03}-action.json',dict(step=step,payload=payload,reply=answer['text']))
            try:a,nextobs,nextinfo,feedback=execute(env,payload,answer['text'])
            except (ValueError,AssertionError,KeyError):outcome='native_action_contract_failure';break
            trajectory.append(a)
            history=copy.deepcopy(body['messages'][1:])+[dict(role='assistant',content=answer['text'])]
            if payload['type']=='stop':outcome='model_stop';break
            obs,info=nextobs,nextinfo;trajectory.append(dict(observation=obs,info=info))
        if outcome!='model_stop':trajectory.append(create_stop_action('Experiment stopped: '+outcome))
        save(folder/'terminal.json',dict(outcome=outcome,final_step=step,injection_step=record['step'],
            reward=score(env,private,trajectory),normal_observation_restored_from_step=record['step']+1,
            semantic_Mirage='pending_audit',downstream_attribution='pending_audit'))
    finally:close_env(env,folder)

def main():
    global STOP
    R.mkdir(exist_ok=False)
    signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True))
    signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
    assert sha(Path(native.__file__).read_bytes())==sha((P/'native-parser-source.py').read_bytes())
    lease=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a')
    fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
    save(R/'site-lease.json',dict(pid=os.getpid(),time=time.time(),site=29980))
    tasks={x['task_id']:x for x in json.loads((P/'tasks.json').read_text())}
    bindings={x['task_id']:x for x in json.loads((P/'native-bindings-public.json').read_text())['tasks']}
    original_goto=Page.goto
    def goto(page,url,**kwargs):
        if kwargs.get('timeout') is None:kwargs['timeout']=120000
        return original_goto(page,url,**kwargs)
    Page.goto=goto
    try:
        state(phase='waiting_for_model')
        for _ in range(240):
            if stopping():raise InterruptedError('Manual stop')
            try:
                r=requests.get(URL+'/health',headers={'Authorization':'Bearer '+TOKEN},timeout=5)
                if r.status_code==200 and r.json().get('ready'):break
            except requests.RequestException:pass
            time.sleep(5)
        else:raise RuntimeError('Model did not become ready')
        auth=R/'.auth';auth.mkdir();renew_comb(['classifieds'],str(auth))
        continuation_queue=[]
        imports=json.loads((P/'reuse-ledger.json').read_text())
        reused={r['task_id']:r for r in imports['completed_natural_trajectories']}
        save(R/'reuse-ledger.json',imports)
        for tid in CFG['task_ids']:
            if tid in reused:
                source=Path(reused[tid]['clean_path'])
                terminal=json.loads((source/'terminal.json').read_text())
                assert terminal['outcome'] in ['model_stop','step_cap']
                assert sha((source/'terminal.json').read_bytes())==reused[tid]['terminal_sha256']
                save(R/f'T{tid:03}'/'reused-clean.json',reused[tid])
                continue
            task=tasks[tid];binding=bindings[tid];raw=Path(binding['original_private_path']).read_bytes()
            assert sha(raw)==binding['original_private_SHA']
            private=R/f'T{tid:03}'/'PRIVATE-evaluation.json'
            config=json.loads(raw.decode().replace('192.0.2.10:19980','192.0.2.10:29980'))
            assert config['require_reset'] is False and config['eval']['eval_types']==['url_match'] and all((P/rel).is_file() for rel in task.get('reference_image_paths',[]))
            config['storage_state']=str(auth/'classifieds_state.json');save(private,config)
            checkpoints=collect_clean(task,private,private.parent/'clean')
            for cp in checkpoints:
                for condition in CFG['conditions'][1:]:
                    continuation_queue.append(dict(task_id=tid,private=str(private),checkpoint=str(cp),condition=condition,
                        folder=str(private.parent/'branches'/cp.name/condition)))
            save(R/'continuation-queue.json',continuation_queue)
        save(R/'initial-phase-completed.json',dict(time=time.time(),model_calls=CALLS,task_ids=CFG['task_ids'],
            planned_continuations=len(continuation_queue),history_policy=CFG['history_policy'],semantic_labels='pending_audit'))
        save(R/'deferred-continuations.json',dict(queue=continuation_queue,executed=False,
            reason='100 natural main trajectories and their initial probes are the current priority; continuation branches are counted separately'))
        completed=[json.loads(f.read_text()) for f in R.glob('T*/clean/terminal.json')]
        assert len(completed)+len(reused)==100
        state(phase='completed_100_natural',new_natural=len(completed),reused_natural=len(reused),
            total_natural=100,semantic_labels='pending_audit',branch_continuations='deferred')
    except BaseException:
        failure=dict(error=traceback.format_exc(),time=time.time(),not_semantic_failure=True)
        save(R/'failure.json',failure);state(phase='stopped' if stopping() else 'failed',**failure);raise
    finally:
        try:rpc('/shutdown',{})
        except Exception:pass
        save(R/'exit.json',dict(time=time.time(),model_calls=CALLS))

if __name__=='__main__':main()
