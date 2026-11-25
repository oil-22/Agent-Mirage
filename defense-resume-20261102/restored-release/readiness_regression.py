"""Source-bound real-image development checks for observation usability, no GUI."""
import argparse,json,time,traceback
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,digest,canonical
from defense.http_backend import RemoteQwen

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
 a.root.mkdir(parents=True,exist_ok=False)
 def load_run(name):
  pointer=json.loads((a.source/'runs'/name/'complete.json').read_text());attempt=Path(pointer['attempt'])
  assert digest((attempt/'complete.json').read_bytes())==pointer['sha256']
  events=[json.loads(l)for l in(attempt/'events.jsonl').read_text().splitlines()]
  return attempt,events
 def reconstruct(attempt,public):
  images=tuple(VisibleImage((attempt/(i['sha256']+'.image')).read_bytes(),i['role'])for i in public['images'])
  assert all(digest(im.raw)==i['sha256']for im,i in zip(images,public['images']))
  return PublicView(public['observation_id'],public['messages'],images,public['recent_action'],public['execution_feedback'],public['observed_at'])
 selected=[]
 for condition,arm in [('blank_replace','joint'),('clean','joint'),('clean','pre_only')]:
  attempt,events=load_run(f'vwa--classifieds_112--{condition}--{arm}')
  last=next(e for e in reversed(events)if e['kind']=='verifier_request'and e['data']['phase']=='screen')
  selected.append((condition+'_'+arm+'_offscreen_or_wrong_page','screen',attempt,last['data']['public'],'usable',last['seq']))
 attempt,events=load_run('vwa--classifieds_112--blank_replace--joint')
 screens=[e for e in events if e['kind']=='verifier_request'and e['data']['phase']=='screen'and not e['data'].get('format_retry',0)]
 normal=screens[0]
 blank=next(e for e in screens if e['data']['public']['observation_id']=='002-obs002')
 focused=next(e for e in events if e['kind']=='verifier_request'and e['data']['phase']=='focus')
 selected += [('normal_initial','screen',attempt,normal['data']['public'],'usable',normal['seq']),
              ('blank_still_blocked','screen',attempt,blank['data']['public'],'not_usable',blank['seq']),
              ('actual_focus_supported','focus',attempt,focused['data']['public'],'usable',focused['seq']),
              ('no_focus_still_unconfirmed','focus',attempt,normal['data']['public'],'not_usable',normal['seq'])]
 manifest=[{'case':case,'phase':phase,'source':str(attempt),'source_event_seq':seq,'public_sha256':digest(canonical(public)),
            'expected':expected,'scope':'Development acceptance only; no Mirage accuracy or live recovery estimate'}for case,phase,attempt,public,expected,seq in selected]
 (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2));results=[]
 model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
 for case,phase,attempt,public,expected,seq in selected:
  view=reconstruct(attempt,public);log=Journal(a.root/case);log.observation(view,audience='source_public')
  c=Controller(model.judge,log,'joint',Limits(probe_observation_readiness=True))
  (a.root/'status.json').write_text(json.dumps({'phase':'running','case':case,'completed':len(results),'time':time.time()}))
  try:
   value=c.inspect('screen',view)if phase=='screen'else c.check_current_focus(view)['focus']
   passed=value['status']=='usable'if expected=='usable'else value['status']!='usable'
   row={'case':case,'phase':phase,'expected':expected,'actual':value,'passed_predeclared_expectation':passed,'verifier_calls':c.verifier_calls}
  except Exception:
   row={'case':case,'passed_predeclared_expectation':False,'error':traceback.format_exc(),'verifier_calls':c.verifier_calls}
  (a.root/(case+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2));results.append(row)
 # Missing observation is checked by control flow, never by pretending it is a model reply.
 log=Journal(a.root/'missing_image');c=Controller(lambda *_:(_ for _ in ()).throw(AssertionError('Judge called without an image')),log,'pre_only',Limits(probe_observation_readiness=True))
 result=c.decide(PublicView('missing',[],()),lambda *_:(_ for _ in ()).throw(AssertionError('Actor called without evidence')),lambda _:None,None)
 row={'case':'missing_image','passed_predeclared_expectation':result['status']=='blocked'and c.actor_calls==0 and c.verifier_calls==0,'verifier_calls':0,'result':result,'engineering_control_not_inference':True}
 results.append(row);(a.root/'missing_image-result.json').write_text(json.dumps(row,indent=2))
 summary={'phase':'completed','passed':all(r['passed_predeclared_expectation']for r in results),'results':results,'cases':len(results),'new_model_calls':sum(r['verifier_calls']for r in results),'scope':'Seven source-bound real-image checks plus one no-image engineering control; no GUI, no efficacy estimate'}
 (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(a.root/'status.json').write_text(json.dumps({'phase':'completed','passed':summary['passed']}))
 print(json.dumps({k:v for k,v in summary.items()if k!='results'}),flush=True)

if __name__=='__main__':main()
