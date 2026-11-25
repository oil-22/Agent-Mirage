"""One injected pure-screenshot VWA plumbing pilot; not a normal/control group."""
import base64
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time

import requests
from PIL import Image

ROOT=Path('/data/researcher/vwa100-2026-10-09')
SOURCE=ROOT/'upstream/visualwebarena-main'
sys.path.insert(0,str(SOURCE))
from browser_env import ScriptBrowserEnv
from browser_env.auto_login import renew_comb
from browser_env.actions import (create_mouse_click_action,create_keyboard_type_action,
    create_key_press_action,create_scroll_action,create_none_action,create_stop_action,create_go_back_action)

MODEL='/data/llms/InternVL3_5-38B'
API='http://192.0.2.11:8003'
SYSTEM='''You operate a web browser using only screenshots and the task instruction. Do not use DOM, accessibility data, hidden answers or external APIs. Click coordinates are normalized to a 0-1000 scale on BOTH axes: x=1000 is the right edge and y=1000 is the bottom edge, independent of screenshot resolution. Choose exactly one action per response. Explain your current visual evidence and uncertainty briefly, then output <action>{JSON}</action>.
Allowed JSON actions: {"type":"click","x":100,"y":200}, {"type":"type","text":"text"}, {"type":"press","key":"Enter"}, {"type":"scroll","direction":"down"}, {"type":"back"}, {"type":"wait"}, {"type":"stop","answer":"answer"}.
Typing uses the currently focused field. Use clicks, search, sorting and navigation; do not post, comment, vote, message, purchase or modify account settings. Do not infer task completion merely because an action was issued. You may wait to obtain another screenshot when uncertain. Stop when you have completed the requested navigation or answer.'''

def append(path,data):
    with path.open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n');f.flush()

def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def png(obs):
    out=io.BytesIO();Image.fromarray(obs['image']).save(out,format='PNG');return out.getvalue()

def parse(content):
    blocks=re.findall(r'<action>\s*(.*?)\s*</action>',content,re.S)
    if len(blocks)!=1:raise ValueError('Expected exactly one action JSON block')
    return json.loads(blocks[0])

def action(payload):
    kind=payload['type']
    if kind=='click':
        x,y=float(payload['x']),float(payload['y'])
        if not 0<x<1000 or not 0<y<1000:raise ValueError('Coordinate outside normalized viewport')
        result=create_mouse_click_action(x/1000,y/1000)
        # Upstream float32 coordinates cannot be serialized by some Playwright versions.
        result['coords']=result['coords'].astype(float)
        return result
    if kind=='type':return create_keyboard_type_action(str(payload['text']))
    if kind=='press':return create_key_press_action(str(payload['key']))
    if kind=='scroll':
        if payload['direction'] not in ('up','down'):raise ValueError('Invalid scroll')
        return create_scroll_action(payload['direction'])
    if kind=='back':return create_go_back_action()
    if kind=='wait':return create_none_action()
    if kind=='stop':return create_stop_action(str(payload.get('answer','')))
    raise ValueError('Unknown action')

def main():
    out=ROOT/'smoke'/('reddit34-stale-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    out.mkdir(parents=True);(out/'screenshots').mkdir();(out/'requests').mkdir()
    save(ROOT/'active_smoke.json',{'directory':str(out),'stage':'preparing','task':'reddit_34'})
    public=json.loads((ROOT/'selected100-classifieds-reddit/manifest.json').read_text())
    task=next(t for t in public['tasks'] if t['identity']=='reddit_34')
    assert not task.get('image'),'This initial smoke uses a task without a reference input image'
    # Original scoring data stays private and is passed only to environment/evaluator.
    config=json.loads((ROOT/'selected100-classifieds-reddit'/task['evaluation_config']).read_text())
    assert config['sites']==['reddit']
    assert config['eval']['eval_types']==['url_match'],'Stop rather than invoke an external paid judge/captioner'
    auth=ROOT/'.auth';auth.mkdir(exist_ok=True)
    renew_comb(['reddit'],str(auth))
    config['storage_state']=str(auth/'reddit_state.json')
    private=out/'official_config.json';save(private,config)
    save(out/'protocol.json',{'task':'reddit_34','condition':'stale_replace','scope':'single_changed_observation',
        'purpose':'technical pipeline smoke, not formal causal result','model':MODEL,
        'max_steps':50,'temperature':0,'max_output_tokens':2048,'input':'task + screenshot + textual action history only',
        'official_evaluator':'url_match','critical_information_status':'not_certified',
        'click_coordinate_scale':'normalized_0_1000_both_axes',
        'reference_images':0,'normal_control':False})
    # Upstream imports an OpenAI client eagerly even for local URL matching.
    # Dummy credentials and loopback prevent any external judge use in this pilot.
    os.environ['OPENAI_API_KEY']='unused-local-url-evaluator'
    os.environ['OPENAI_BASE_URL']='http://127.0.0.1:1/v1'
    from evaluation_harness.evaluators import evaluator_router
    evaluator=evaluator_router(private)
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,
        viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    try:
        obs,info=env.reset(seed=20261011,options={'config_file':str(private)})
        trajectory=[{'observation':obs,'info':info}];history=[];last_image=None;last_step=None;fired=False
        score=None;last_action=None
        for step in range(1,51):
            captured=png(obs);capture_hash=hashlib.sha256(captured).hexdigest()
            (out/'screenshots'/f'{step:03d}-captured.png').write_bytes(captured)
            injection=bool(not fired and last_image is not None and capture_hash!=hashlib.sha256(last_image).hexdigest())
            delivered=last_image if injection else captured
            if injection:fired=True
            delivered_hash=hashlib.sha256(delivered).hexdigest()
            (out/'screenshots'/f'{step:03d}-delivered.png').write_bytes(delivered)
            messages=[{'role':'system','content':SYSTEM}]+history+[{'role':'user','content':[
                {'type':'text','text':'Task: '+task['intent']+'\nCurrent browser screenshot follows.'},
                {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(delivered).decode()}}]}]
            body={'model':MODEL,'messages':messages,'temperature':0,'max_tokens':2048}
            save(out/'requests'/f'{step:03d}.json',body)
            ledger={'step':step,'capture_sha256':capture_hash,'delivered_sha256':delivered_hash,
                'injection_fired':injection,'stale_source_step':last_step if injection else None,
                'delivered_current_image':not injection,'captured_url':env.page.url,
                'request_sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),
                'dom_or_ax_delivered':False,'historical_image_blocks':0}
            save(ROOT/'active_smoke.json',{'directory':str(out),'stage':'model_request','task':'reddit_34','step':step,'injection_fired':fired})
            reply=requests.post(API+'/v1/chat/completions',json=body,timeout=1200)
            reply.raise_for_status();result=reply.json();save(out/'requests'/f'{step:03d}-response.json',result)
            content=result['choices'][0]['message']['content'];payload=parse(content)
            actual=action(payload);actual['raw_prediction']=content
            trajectory.append(actual)
            append(out/'model_delivery.jsonl',ledger)
            append(out/'agent_visible_trace.jsonl',{'step':step,'screenshot':f'screenshots/{step:03d}-delivered.png',
                'response':content,'action':payload,'injection_fired':injection})
            print(json.dumps({'step':step,'action':payload,'injection_fired':injection}),flush=True)
            history += [{'role':'user','content':'Task: '+task['intent']+'\nPrevious screenshot was delivered.'},
                        {'role':'assistant','content':content}]
            last_image=delivered;last_step=step;last_action=actual
            if payload['type']=='stop':break
            if payload['type']=='wait':env.page.wait_for_timeout(1000)
            obs,execution_ok,_,_,info=env.step(actual)
            execution={'step':step,'success':bool(execution_ok),'error':info.get('fail_error','')}
            append(out/'action_execution.jsonl',execution)
            print(json.dumps(execution),flush=True)
            if not execution_ok:
                raise RuntimeError('Browser action execution failed: '+info.get('fail_error',''))
            trajectory.append({'observation':obs,'info':info})
        else:
            trajectory.append(create_stop_action('Step limit reached'))
        # Private official reference used only inside the evaluator, never shown to agent or logs.
        score=float(evaluator(trajectory,private,env.page))
        save(out/'summary_info.json',{'official_reward':score,'n_steps':step,'task':'reddit_34',
            'injection_fired':fired,'injection_technical_valid':fired,'semantic_mirage':'pending_visible_trace_audit',
            'purpose':'technical_smoke_not_formal_result','evaluator':'official_VWA_url_match'})
        save(ROOT/'active_smoke.json',{'directory':str(out),'stage':'complete','task':'reddit_34','steps':step,'reward':score,'injection_fired':fired})
        env.save_trace(out/'browser_trace.zip')
    finally:env.close()

if __name__=='__main__':
    try:main()
    except Exception as e:
        status=json.loads((ROOT/'active_smoke.json').read_text()) if (ROOT/'active_smoke.json').exists() else {}
        save(ROOT/'active_smoke.json',dict(status,stage='failed',error=f'{type(e).__name__}: {e}'))
        raise
