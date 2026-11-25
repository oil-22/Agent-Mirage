"""Real-model diagnostic only: no native actor, GUI action or evaluator."""
import argparse,hashlib,json,sys,time,traceback
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError,canonical,digest,checked_wait
from defense.http_backend import RemoteQwen
from native_direction_consistency import check_direction

def main(root):
    assert not(root/'status.json').exists(),'Never rerun an existing attempt'
    plan=json.loads((root/'plan.json').read_bytes());assert plan['max_calls']==24 and not plan['formal_release']
    model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'));results=[]
    def save(name,value):
        with(root/name).open('x',encoding='utf-8')as f:json.dump(value,f,ensure_ascii=False,indent=2)
    def status(**kw):(root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),'completed':len(results),**kw}),encoding='utf-8')
    try:
        for n,h in json.loads((root/'source-sha256.json').read_bytes()).items():assert digest((root/n).read_bytes())==h,n
        sys.path.insert(0,'/data/researcher/vwa100-2026-10-09')
        from run_reddit_internvl_smoke import parse,action
        source=Path('/data/researcher/vwa100-2026-10-09/run_reddit_internvl_smoke.py')
        save('native-parser-binding.json',{'path':str(source),'sha256':digest(source.read_bytes()),'only_native_parser_and_constructor_used':True,'browser_environment_created_by_worker':False})
        health=model.health();assert health['phase']=='ready'and health['dtype']=='BF16'and health['backend']=='sdpa'
        for case in plan['cases']:
            status(phase='running',case=case['id']);raw=(root/case['packet']).read_bytes();assert digest(raw)==case['packet_sha256'];packet=json.loads(raw);pub=packet['public']
            view=PublicView(pub['observation_id'],pub['messages'],tuple(VisibleImage((root/'images'/(im['sha256']+'.png')).read_bytes(),im['role'])for im in pub['images']),pub['recent_action'],pub['execution_feedback'],pub['observed_at']);assert canonical(view.data())==canonical(pub)
            log=Journal(root/'journal'/case['id']);start=len(model.calls)
            def judge(system,v,candidate):
                if len(model.calls)>=plan['max_calls']:raise RuntimeError('Independent24callcap reached; preserve without extra retries')
                answer=model.judge(system,v,candidate);status(phase='running',case=case['id']);return answer
            controller=Controller(judge,log,'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
            proposal=None;candidate=packet.get('candidate')
            if candidate is not None:
                native=parse(candidate);action(native)
                proposal={'name':native['type'],'payload':native,'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
            try:
                result=controller.inspect('screen'if case['mode']=='screen'else'verify',view,candidate,proposal)
                outcome={'contract_status':'valid','verdict':result}
            except ValidationError as error:outcome={'contract_status':'rejected','reason':str(error),'semantic_mirage':None}
            row={'id':case['id'],'mode':case['mode'],**outcome,'calls':model.calls[start:],'new_actor_calls':0,'model_controlled_GUI_actions':0,
                 'candidate_origin':packet.get('candidate_origin'),'native_WAIT_excluded':checked_wait(proposal)if proposal else None,
                 'direction_check':check_direction(candidate,proposal)if proposal else None,'semantic_pass':None}
            results.append(row);save(case['id']+'-result.json',row)
        save('summary.json',{'phase':'completed','results':results,'calls':model.calls,'new_model_calls':len(model.calls),'new_actor_calls':0,
             'GUI_actions_by_model':0,'official_scores':0,'paid_API_calls':0,'formal_release':False,'new_natural_actor_WAIT_obtained':False,
             'scope':'6scene reads and4authored source-bound candidate probes, nonblind development. Original checker validators/retry budgets preserved, no task trajectory.'})
        status(phase='completed')
    except BaseException:
        save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');raise
    finally:
        save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'terminal-sha256.json','worker.log'}})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();main(a.root)
