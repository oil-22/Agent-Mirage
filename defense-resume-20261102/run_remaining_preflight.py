"""New linked continuation of unexecuted controls; no old terminal request replay."""
import argparse,json,pathlib,time,traceback
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError,canonical,digest
from defense.http_backend import RemoteQwen
from appearance_absence_source import check_appearance_absence

def main(a):
 root=a.root;plan=json.loads((root/'resume-plan.json').read_bytes())
 assert plan['prior_submitted_model_calls']==1 and plan['max_new_calls']==23
 for n,h in json.loads((root/'sealed-inputs.json').read_bytes()).items():assert digest((root/n).read_bytes())==h,n
 model=RemoteQwen(a.url,a.token_file);assert model.health()['phase']=='ready'
 results=[];issued=0;shared_cache={};failure=False
 def save(n,value):
  with(root/n).open('x',encoding='utf-8')as f:json.dump(value,f,ensure_ascii=False,indent=2)
 def status(**kw):
  (root/'status.json').write_text(json.dumps({'time':time.time(),'pid':__import__('os').getpid(),'submitted_new_calls':issued,'returned_new_calls':len(model.calls),'completed_new_controls':len(results),**kw}))
 try:
  for case in plan['remaining_cases']:
   identity=case['id'];packet=json.loads((root/case['packet']).read_bytes());pub=packet['public'];start=issued
   status(phase='running',case=identity)
   def image(im):
    raw=(root/'images'/(im['sha256']+'.png')).read_bytes();assert digest(raw)==im['sha256'];return VisibleImage(raw,im['role'])
   view=PublicView(pub['observation_id'],pub['messages'],tuple(image(im)for im in pub['images']),pub['recent_action'],pub['execution_feedback'],pub['observed_at']);assert canonical(view.data())==canonical(pub)
   def judge(system,v,candidate):
    nonlocal issued
    if issued>=23:raise RuntimeError('Original aggregate24-call cap reached including prior failure')
    issued+=1;status(phase='running',case=identity)
    return model.judge(system,v,candidate)
   c=Controller(judge,Journal(root/'journal'/identity),'joint',Limits(probe_history_reports=True),sleeper=lambda _:None);c.person_frame_cache=shared_cache
   c.reference_bank=[{'observation_id':im['observation_id'],'image':image(im),'candidate':im['candidate']}for im in packet['reference_bank']]
   try:
    if case['mode']=='verify':outcome=c.inspect('verify',view,packet['candidate'],packet['proposal'])
    else:outcome=check_appearance_absence(c,view,packet['candidate'],{'name':'wait'if case['mode']=='routing'else'scroll'})
    result={'contract_status':'valid','result':outcome}
   except ValidationError as e:result={'contract_status':'rejected','reason':str(e),'semantic_mirage':None}
   shared_cache=c.person_frame_cache
   row={'id':identity,'mode':case['mode'],**result,'submitted_calls':issued-start,'returned_calls':model.calls,'semantic_pass':None};results.append(row);save(identity+'-result.json',row)
  save('summary.json',{'phase':'completed_remaining_controls','results':results,'submitted_new_calls':issued,'prior_submitted_calls':1,'calls':model.calls,'not_rerun':plan['excluded_cases'],'formal_release':False,'GUI_actions':0,'actor_calls':0,'official_scores':0,'paid_API_calls':0});status(phase='completed_remaining_controls')
 except BaseException:
  failure=True;save('failure.json',{'traceback':traceback.format_exc(),'submitted_calls':issued,'returned_calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');traceback.print_exc()
 finally:
  save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in ['terminal-sha256.json','worker.log']})
 if failure:raise SystemExit(1)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--url',required=True);p.add_argument('--token-file',type=pathlib.Path,required=True);main(p.parse_args())
