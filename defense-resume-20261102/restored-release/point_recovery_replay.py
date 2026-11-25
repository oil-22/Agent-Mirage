"""Real source-bound strict rejection, valid point, target mismatch, WAIT/direction controls."""
import argparse,copy,json,time,traceback
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
 events=[json.loads(l)for l in(a.source/'events.jsonl').read_text().splitlines()]
 req=next(e for e in reversed(events)if e['kind']=='verifier_request'and e['data']['phase']=='point'and e['data']['format_retry']==0)
 p=req['data']['public'];view=PublicView(p['observation_id'],copy.deepcopy(p['messages']),tuple(VisibleImage((a.source/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images']),p['recent_action'],p['execution_feedback'],p['observed_at']);assert canonical(view.data())==canonical(p)
 expectations=[('source_uncertified_point','strict rejection or validated nonbutton; never certify a button at the original gap'),('actual_first_page_control','button at525,896; visible first-page double chevron'),('background','background at100,100'),('matching_first_page','supported'),('wrong_page_four','contradicted'),('pure_wait','supported pure nativeWAIT'),('up_prose_down_json','not supported')]
 manifest={'source':str(a.source),'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'source_point_request_seq':req['seq'],'source_public_sha256':digest(canonical(p)),'predeclared_controls':expectations,'expected_labels_not_model_inputs':True,'scope':'Nonblind development on one current real source screenshot. Original strict point reader may remain unavailable; no invalid evidence is upgraded. Not labels, task success or efficacy.'}
 (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2));model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[];frozen=None
 def run(name,callback):
  (a.root/'status.json').write_text(json.dumps({'phase':'running','case':name,'time':time.time()}));log=Journal(a.root/name);c=Controller(model.judge,log,'post_only',Limits());before=len(model.calls);log.observation(view,audience='source_public')
  try:row=callback(c);row.update(case=name,verifier_calls=c.verifier_calls,receipts=model.calls[before:])
  except Exception:row={'case':name,'passed':False,'error':traceback.format_exc(),'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
  row['events_sha256']=digest((log.root/'events.jsonl').read_bytes());results.append(row);(a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
 def original(c):
  try:
   v=c.inspect('point',view,req['data']['mechanical_original_query']);return {'passed':v['kind']in{'background','content','unknown'},'reading':v,'invalid_reading_accepted':False}
  except ValidationError as e:
   return {'passed':str(e)=='Point not inside current point evidence','strict_rejection':str(e),'invalid_reading_accepted':False}
 run('source_uncertified_point',original)
 def point(c,x,y):return c.check_current_point(view,{'name':'click','parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':{'type':'click','x':x,'y':y}},'unknown')['point']
 def proper(c):
  nonlocal frozen
  frozen=point(c,525,896);return {'passed':frozen['kind']=='button'and frozen['visible_text'].strip()in{'«','<<','≪','‹‹'},'reading':frozen}
 run('actual_first_page_control',proper)
 def background(c):
  v=point(c,100,100);return {'passed':v['kind']=='background'and not v['visible_text'].strip(),'reading':v}
 run('background',background)
 for name,text,expected in [('matching_first_page','I will navigate to the first page.','supported'),('wrong_page_four','I will click page 4.','contradicted')]:
  def alignment(c,text=text,expected=expected):
   assert frozen is not None
   raw=text+'\n<action>{"type":"click","x":525,"y":896}</action>';proposal={'name':'click','parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':{'type':'click','x':525,'y':896}}
   v=c.check_target_alignment(view,raw,proposal,frozen)['result'];return {'passed':v['action']['status']==expected,'verdict':v}
  run(name,alignment)
 for name,raw,payload in [('pure_wait','I will wait.\n<action>{"type":"wait"}</action>',{'type':'wait'}),('up_prose_down_json','I will scroll upward.\n<action>{"type":"scroll","direction":"down"}</action>',{'type':'scroll','direction':'down'})]:
  def verify(c,name=name,raw=raw,payload=payload):
   proposal={'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':payload};v=c.inspect('verify',view,raw,proposal)
   return {'passed':(v['pure_wait']and v['action']['status']=='supported')if name=='pure_wait'else v['action']['status']!='supported','verdict':v}
  run(name,verify)
 summary={'phase':'completed','passed':len(results)==7 and all(x['passed']for x in results),'results':results,'model_calls':len(model.calls),'scope':manifest['scope']};(a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(a.root/'status.json').write_text(json.dumps({'phase':'completed','passed':summary['passed'],'time':time.time()}));print(json.dumps({'passed':summary['passed']}))
if __name__=='__main__':main()
