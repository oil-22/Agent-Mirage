"""Once-only source-bound controls. No actor, browser, scorer or private labels."""
import argparse,json,time,traceback
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError,canonical,digest
from defense.http_backend import RemoteQwen
from appearance_absence_source import check_appearance_absence

def main(root):
 plan=json.loads((root/'plan.json').read_bytes());assert plan['max_calls']==24 and not(root/'status.json').exists()
 model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'));results=[];shared_cache={}
 def save(n,x):
  with(root/n).open('x',encoding='utf-8')as f:json.dump(x,f,ensure_ascii=False,indent=2)
 def status(**kw):(root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),'completed':len(results),**kw}))
 try:
  for n,h in json.loads((root/'source-sha256.json').read_bytes()).items():assert digest((root/n).read_bytes())==h,n
  assert model.health()['phase']=='ready'
  for case in plan['cases']:
   status(phase='running',case=case['id']);raw=(root/case['packet']).read_bytes();assert digest(raw)==case['packet_sha256'];packet=json.loads(raw);pub=packet['public'];start=len(model.calls)
   def image(im):return VisibleImage((root/'images'/(im['sha256']+'.png')).read_bytes(),im['role'])
   v=PublicView(pub['observation_id'],pub['messages'],tuple(image(im)for im in pub['images']),pub['recent_action'],pub['execution_feedback'],pub['observed_at']);assert canonical(v.data())==canonical(pub)
   def judge(system,p,c):
    if len(model.calls)>=24:raise RuntimeError('Independent24callcap reached')
    result=model.judge(system,p,c);status(phase='running',case=case['id']);return result
   c=Controller(judge,Journal(root/'journal'/case['id']),'joint',Limits(probe_history_reports=True),sleeper=lambda _:None);c.person_frame_cache=shared_cache
   c.reference_bank=[{'observation_id':im['observation_id'],'image':image(im),'candidate':im['candidate']}for im in packet['reference_bank']]
   proposal={'name':'wait'if case['mode']=='routing'else 'scroll'}
   try:
    if case['mode']=='verify':outcome=c.inspect('verify',v,packet['candidate'],packet['proposal'])
    else:outcome=check_appearance_absence(c,v,packet['candidate'],proposal)
    result={'contract_status':'valid','result':outcome}
   except ValidationError as e:result={'contract_status':'rejected','reason':str(e),'semantic_mirage':None}
   shared_cache=c.person_frame_cache
   row={'id':case['id'],'mode':case['mode'],**result,'calls':model.calls[start:],'semantic_pass':None};results.append(row);save(case['id']+'-result.json',row)
  save('summary.json',{'phase':'completed','results':results,'calls':model.calls,'new_model_calls':len(model.calls),'actor_model_calls':0,'GUI_actions':0,'official_scores':0,'paid_API_calls':0,'formal_release':False});status(phase='completed')
 except BaseException:
  save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');traceback.print_exc();raise SystemExit(1)
 finally:save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'worker.log','terminal-sha256.json'}})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
