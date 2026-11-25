"""New actor-control extension using sealed readouts, within the original 31-call development ceiling."""
import argparse,copy,json,os,sys,time,traceback
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();root=a.root
 plan=json.loads((root/'plan.json').read_bytes());parent=Path(plan['parent_root'])
 sys.path.insert(0,str(parent/'release'))
 from source_evidence_preview_dev import read_view,preview_view,CAUTION
 from defense.core import Journal,canonical,digest,validate_screen
 from defense.http_backend import RemoteQwen
 seals=json.loads((parent/'terminal-sha256.json').read_bytes())
 assert digest((parent/'summary.json').read_bytes())==plan['parent_summary_sha256']
 for n,h in seals.items():assert digest((parent/n).read_bytes())==h,n
 old=json.loads((parent/'summary.json').read_bytes());assert old['new_model_calls']+6<=31
 assert not(root/'status.json').exists()
 log=Journal(root/'journal');model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'));results=[]
 def save(n,d):
  with(root/n).open('x',encoding='utf-8')as f:json.dump(d,f,ensure_ascii=False,indent=2)
 def status(**k):(root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),**k}))
 try:
  for name in plan['cases']:
   original=next(c for c in json.loads((parent/'plan.json').read_bytes())['cases']if c['id']==name)
   assert not original['actor_pair'],'Only previously unattempted actor controls'
   view=read_view(json.loads((parent/original['packet']).read_bytes())['public'],parent/'images');pv=preview_view(view)
   result=json.loads((parent/(name+'-result.json')).read_bytes());reading=validate_screen(copy.deepcopy(result['preview']),pv)
   feedback=CAUTION+'\nCANDIDATE-BLIND CURRENT-IMAGE READING (fallible verifier output, not task truth; compare with original screenshot, and preserve all stated limitations):\n'+json.dumps({'source_observation_id':pv.observation_id,'source_image_sha256':digest(pv.images[0].raw),'reading':reading},ensure_ascii=False)
   log.observation(view,audience='previously_unattempted_actor_control');row={'id':name,'preview_reuse_parent_result_sha256':digest((parent/(name+'-result.json')).read_bytes()),'arms':[]}
   for arm,extra in [('baseline',None),('evidence',feedback)]:
    status(phase='running',case=name,arm=arm,completed=len(results));template=json.loads((parent/'release/native-vwa-request.json').read_bytes())
    body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=copy.deepcopy(view.messages)
    if extra is not None:body['messages'].append({'role':'user','content':extra})
    assert body['messages'][:len(view.messages)]==view.messages
    log.append('development_actor_request',{'case':name,'arm':arm,'body':body,'original_public_sha256':digest(canonical(view.data()))})
    before=len(model.calls);candidate=model.actor(body);record={'arm':arm,'candidate':candidate,'calls':model.calls[before:]}
    log.append('development_actor_response',{'case':name,**record});row['arms'].append(record);save(name+'-'+arm+'.json',record)
   results.append(row);save(name+'-result.json',row)
  save('summary.json',{'phase':'completed','new_model_calls':len(model.calls),'parent_calls':old['new_model_calls'],'combined_calls':old['new_model_calls']+len(model.calls),'predeclared_combined_ceiling':31,'results':results,'calls':model.calls,'new_gui_actions':0,'official_evaluations':0,'scope':'New actor-control inputs, sealed exact preview reuse, no retrial of any completed actor condition; nonblind single-task development.'});status(phase='completed',completed=len(results))
 except BaseException:
  save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'completed':len(results),'semantic_mirage':None});status(phase='technical_failure',completed=len(results));raise
 finally:save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'worker.log','terminal-sha256.json'}})

if __name__=='__main__':main()
