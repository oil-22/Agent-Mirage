"""New source-bound real development. No GUI; no old completed controls rerun."""
import argparse
import copy
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, canonical, digest
from defense.http_backend import RemoteQwen


def main(root):
    assert not(root/'status.json').exists(),'Immutable attempt: no relaunch'
    manifest=json.loads((root/'source-sha256.json').read_bytes())
    for n,h in manifest.items():assert digest((root/n).read_bytes())==h,n
    plan=json.loads((root/'plan.json').read_bytes())
    assert plan['max_calls']==24 and plan['formal_trial']is False
    source=Path('/data/researcher/vwa100-2026-10-09');sys.path.insert(0,str(source))
    from run_reddit_internvl_smoke import parse,action,SYSTEM
    template=json.loads((root/'release/native-vwa-request.json').read_bytes())
    assert template['max_tokens']==2048 and template['messages'][0]['content'].startswith(SYSTEM)
    native_source=source/'run_reddit_internvl_smoke.py'
    model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'))
    health=model.health();assert health['phase']=='ready'and health['dtype']=='BF16'and health['backend']=='sdpa'
    results=[]
    def save(n,x):
        with(root/n).open('x',encoding='utf-8')as f:json.dump(x,f,ensure_ascii=False,indent=2)
    def status(**kw):
        (root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),'completed':len(results),**kw}),encoding='utf-8')
    save('native-parser-source-binding.json',{'path':str(native_source),'sha256':digest(native_source.read_bytes()),'source_changed':False,'GUI_environment_created':False})
    def budget():
        if len(model.calls)>=plan['max_calls']:raise RuntimeError('Predeclared24 total-call development cap reached; no budget expansion')
    def parser(text):
        payload=parse(text)
        if payload['type']=='tab':
            raise ValueError('Tab ownership/live context unavailable in archived no-GUI development')
        action(payload)  # Original native constructor/type/coordinate validation, no env.step.
        return {'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
    try:
        for case in plan['cases']:
            status(phase='running',case=case['id'])
            packet=(root/case['packet']).read_bytes();assert digest(packet)==case['packet_sha256'];pub=json.loads(packet)['public']
            images=tuple(VisibleImage((root/'images'/(im['sha256']+'.png')).read_bytes(),im['role'])for im in pub['images'])
            view=PublicView(pub['observation_id'],pub['messages'],images,pub['recent_action'],pub['execution_feedback'],pub['observed_at'])
            assert canonical(view.data())==canonical(pub)
            log=Journal(root/'journal'/case['id']);before=len(model.calls)
            def actor(v,corrections):
                budget();body={k:copy.deepcopy(val)for k,val in template.items()if k!='messages'};body['messages']=copy.deepcopy(v.messages)
                assert body['messages'][:len(view.messages)]==view.messages
                return model.actor(body)
            def judge(system,v,candidate):
                budget();return model.judge(system,v,candidate)
            c=Controller(judge,log,'post_only',Limits(),sleeper=lambda _:None)
            result=c.decide(view,actor,parser,None)
            row={'id':case['id'],'result':result,'calls':model.calls[before:],'actor_calls':c.actor_calls,
                 'verifier_calls':c.verifier_calls,'new_GUI_actions':0,'semantic_mirage':None,
                 'not_a_live_recapture_or_trajectory_trial':True}
            results.append(row);save(case['id']+'-result.json',row)
        save('summary.json',{'phase':'completed','results':results,'calls':model.calls,'new_model_calls':len(model.calls),
             'new_GUI_actions':0,'official_scores':0,'formal_release':False,'new_real_WAIT_control_passed':False,
             'scope':'Four new full native public prefixes, selected nonblind one-task development; initial candidate retained, original strict checker and native parser unchanged; no efficacy inference'})
        status(phase='completed')
    except BaseException:
        save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');raise
    finally:
        save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'worker.log','terminal-sha256.json'}})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();main(a.root)
