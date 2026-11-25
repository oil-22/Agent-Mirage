"""Bounded source-attribution development; no real actor, GUI or scorer."""
import argparse,copy,json,sys,time,traceback
from dataclasses import replace
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError,canonical,digest,checked_wait
from defense.http_backend import RemoteQwen
from strict_price_comparison import check_strict_price_comparison

def main(root):
    assert not(root/'status.json').exists();plan=json.loads((root/'plan.json').read_bytes());assert plan['max_calls']==16 and not plan['formal_release']
    model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'));results=[]
    def save(n,x):
        with(root/n).open('x',encoding='utf-8')as f:json.dump(x,f,ensure_ascii=False,indent=2)
    def status(**kw):(root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),'completed':len(results),**kw}))
    try:
        for n,h in json.loads((root/'source-sha256.json').read_bytes()).items():assert digest((root/n).read_bytes())==h,n
        sys.path.insert(0,'/data/researcher/vwa100-2026-10-09');from run_reddit_internvl_smoke import parse,action
        source=Path('/data/researcher/vwa100-2026-10-09/run_reddit_internvl_smoke.py');save('native-parser-binding.json',{'path':str(source),'sha256':digest(source.read_bytes()),'browser_created':False})
        h=model.health();assert h['phase']=='ready'and h['dtype']=='BF16'and h['backend']=='sdpa'
        for case in plan['cases']:
            status(phase='running',case=case['id']);raw=(root/case['packet']).read_bytes();assert digest(raw)==case['packet_sha256'];packet=json.loads(raw);pub=packet['public']
            image=lambda h,role:VisibleImage((root/'images'/(h+'.png')).read_bytes(),role)
            view=PublicView(pub['observation_id'],pub['messages'],tuple(image(im['sha256'],im['role'])for im in pub['images']),pub['recent_action'],pub['execution_feedback'],pub['observed_at']);assert canonical(view.data())==canonical(pub)
            log=Journal(root/'journal'/case['id']);start=len(model.calls)
            def judge(system,v,candidate):
                if len(model.calls)>=plan['max_calls']:raise RuntimeError('Independent16callcap reached')
                answer=model.judge(system,v,candidate);status(phase='running',case=case['id']);return answer
            c=Controller(judge,log,'joint',Limits(),sleeper=lambda _:None)
            c.reference_bank=[{'observation_id':r['observation_id'],'image':image(r['image_sha256'],'current'),'candidate':r['candidate']}for r in packet['reference_bank']]
            try:
                if case['mode']=='relation':
                    pair={'original_completion_image_reading':packet['completion_reading'],'frozen_source_frame_records':packet['source_records'],'scope':'Isolated exact/explicit authored source claim, not entire original completion or minimum'}
                    text=json.dumps(pair,ensure_ascii=False);comparison=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='');log.observation(comparison,audience='completion_frame_price_text_relation');outcome=c.inspect('completion_source_relation',comparison,text)
                elif case['mode']=='completion':outcome=c.inspect('completion',view)
                else:
                    native=parse(packet['candidate']);action(native);proposal={'name':native['type'],'payload':native,'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
                    outcome={'pure_native_WAIT':checked_wait(proposal),'strict_comparison':check_strict_price_comparison(packet['candidate'],proposal),'scope':'Zero-call authored WAIT or ambiguous actual322 route; not semantic result'}
                result={'contract_status':'valid','result':outcome}
            except ValidationError as error:result={'contract_status':'rejected','reason':str(error),'semantic_mirage':None}
            row={'id':case['id'],'mode':case['mode'],**result,'calls':model.calls[start:],'actor_model_calls':0,'GUI_actions':0,'semantic_pass':None};results.append(row);save(case['id']+'-result.json',row)
        save('summary.json',{'phase':'completed','results':results,'new_model_calls':len(model.calls),'calls':model.calls,'actor_model_calls':0,'GUI_actions':0,'official_scores':0,'paid_API_calls':0,'formal_release':False,'scope':'Selected same-task source-attribution controls; prefrozen price readings reused as data in relation cases, unseeded full-completion audit separate. Not efficacy, natural WAIT or independent task sample.'});status(phase='completed')
    except BaseException:
        save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');traceback.print_exc();raise SystemExit(1)
    finally:save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'terminal-sha256.json','worker.log'}})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);main(ap.parse_args().root)
