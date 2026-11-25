"""Two new feedback-condition diagnostics, using the remaining two calls of the frozen ceiling."""
import argparse,copy,json,sys,time,traceback
from pathlib import Path

ROUTING = '''SOURCE-AND-EXECUTION CONTRACT FOR THIS RESPONSE.
The current-image reading below is fallible evidence, not a certified answer. Compare it with the original
screenshot. Earlier assistant page labels and click intentions are reports, not independent confirmation of
the CURRENT page. Where the current reading says that an identifier or control is not visible, do not assert
that identifier or click a remembered control merely because earlier assistant text repeats it. You can
describe the visible layout and seek the missing evidence without guessing a page number or claiming coverage.
The native action JSON is what the environment will execute. For native scroll, up moves toward earlier/above
page content; down moves toward later/below page content. Select a justified action using the actual task and
screen, then ensure the explanation describes that same native action. This contract does not select a target
or a direction for you. Keep the original explanation-then-<action> format and one allowed native action.'''

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();root=a.root
 plan=json.loads((root/'plan.json').read_bytes());parent=Path(plan['parent_root']);sys.path.insert(0,str(parent/'release'))
 from source_evidence_preview_dev import read_view,preview_view,CAUTION
 from defense.core import Journal,canonical,digest,validate_screen
 from defense.http_backend import RemoteQwen
 for n,h in json.loads((parent/'terminal-sha256.json').read_bytes()).items():assert digest((parent/n).read_bytes())==h,n
 assert plan['prior_calls']==29 and plan['max_new_calls']==2 and plan['combined_ceiling']==31
 assert not(root/'status.json').exists()
 log=Journal(root/'journal');model=RemoteQwen('http://192.0.2.11:18127',Path('/data/researcher/mirage-defense-pilot-20261023/transport.token'));results=[]
 def save(n,d):
  with(root/n).open('x',encoding='utf-8')as f:json.dump(d,f,ensure_ascii=False,indent=2)
 def status(**k):(root/'status.json').write_text(json.dumps({'time':time.time(),'calls':len(model.calls),**k}))
 try:
  for name in plan['cases']:
   status(phase='running',case=name,completed=len(results));case=next(c for c in json.loads((parent/'plan.json').read_bytes())['cases']if c['id']==name)
   view=read_view(json.loads((parent/case['packet']).read_bytes())['public'],parent/'images');pv=preview_view(view)
   reading=validate_screen(copy.deepcopy(json.loads((parent/(name+'-result.json')).read_bytes())['preview']),pv)
   feedback=CAUTION+'\n'+ROUTING+'\nCANDIDATE-BLIND CURRENT-IMAGE READING (fallible, not task truth):\n'+json.dumps({'source_observation_id':pv.observation_id,'source_image_sha256':digest(pv.images[0].raw),'reading':reading},ensure_ascii=False)
   template=json.loads((parent/'release/native-vwa-request.json').read_bytes());body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'}
   body['messages']=copy.deepcopy(view.messages)+[{'role':'user','content':feedback}];assert body['messages'][:-1]==view.messages
   log.observation(view,audience='new_feedback_condition_diagnostic');log.append('development_actor_request',{'case':name,'arm':'evidence_routing','body':body,'original_public_sha256':digest(canonical(view.data()))})
   before=len(model.calls);candidate=model.actor(body);r={'arm':'evidence_routing','candidate':candidate,'calls':model.calls[before:]}
   log.append('development_actor_response',{'case':name,**r});save(name+'-evidence_routing.json',r);results.append({'id':name,'arms':[r]})
  save('summary.json',{'phase':'completed','new_model_calls':len(model.calls),'combined_calls':29+len(model.calls),'predeclared_combined_ceiling':31,'results':results,'calls':model.calls,'new_gui_actions':0,'official_evaluations':0,'scope':'Two selected nonblind new-feedback-condition diagnostics following preserved v1 failures. Not independent validation, no fair isolation of routing vs general added instruction, no formal efficacy estimate.'});status(phase='completed',completed=len(results))
 except BaseException:
  save('failure.json',{'traceback':traceback.format_exc(),'calls':model.calls,'semantic_mirage':None});status(phase='technical_failure');raise
 finally:save('terminal-sha256.json',{str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob('*')if p.is_file()and p.name not in {'worker.log','terminal-sha256.json'}})

if __name__=='__main__':main()
