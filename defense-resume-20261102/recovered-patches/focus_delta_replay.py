"""Targeted regression: retain unchanged actual v2.7 replies, add independent focus reads.

This is explicitly incremental, not a fresh 14-case inference or an accuracy estimate.
"""
import argparse,ast,copy,json,time,traceback,hashlib
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--parent',type=Path,required=True);ap.add_argument('--parent-release',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
 release=Path(__file__).resolve().parent;a.root.mkdir(parents=True,exist_ok=False)
 for name in ['defense/prompts.py','defense/schema.py','defense/qwen_backend.py','native-vwa-request.json','plan80.json']:
  assert(a.parent_release/name).read_bytes()==(release/name).read_bytes(),name
 def methods(path):
  tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Controller')
  return{n.name:ast.dump(n)for n in cls.body if isinstance(n,ast.FunctionDef)}
 before=methods(a.parent_release/'defense/core.py');after=methods(release/'defense/core.py')
 for name in ['reference_view','remember','check_current_point']:assert before[name]==after[name],name
 parent_summary=json.loads((a.parent/'summary.json').read_text());assert parent_summary['cases']==13 and parent_summary['protocol_valid']==13
 rows=json.loads((a.parent/'results.json').read_text());manifest=json.loads((a.parent/'manifest.json').read_text())
 by={m['category']:m for m in manifest};model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
 def load(source,obs):
  p=Path(source);events=[json.loads(x)for x in p.read_text().splitlines()]
  pub=next(e['data']['public']for e in events if e['kind']=='observation'and e['data']['public']['observation_id']==obs)
  ims=tuple(VisibleImage((p.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in pub['images'])
  return PublicView(pub['observation_id'],pub['messages'],ims,pub['recent_action'],pub['execution_feedback'],pub['observed_at']),events
 calls=0
 for row in rows:
  row['main_result_reused_from']=str(a.parent/'results.json');row['model_calls_this_attempt']=0
  if 'point_probe'in row:row['point_result_reused_from']=str(a.parent/'results.json')
  if row['category']in {'missing_observation','stale_observation'}:
   m=by[row['category']];v,_=load(m['source'],m['observation_id']);log=Journal(a.root/row['category']);c=Controller(model.judge,log)
   try:
    cross=c.check_current_focus(v);row.update(focus_probe=cross['focus'],focus_agrees=cross['agrees'])
   except Exception:row.update(protocol_valid=False,error=traceback.format_exc())
   row['model_calls_this_attempt']=c.verifier_calls;calls+=c.verifier_calls
  (a.root/'results.json').write_text(json.dumps(rows,indent=2))
 source=Path(by['normal_candidate']['source']);v,events=load(source,'002-obs002')
 candidate=next(e['data']['text']for e in events if e['kind']=='candidate'and e['data']['observation_id']=='002-obs002')
 payload=json.loads(candidate.split('<action>',1)[1].split('</action>',1)[0]);assert payload['type']=='type'
 proposal={'name':'type','payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
 log=Journal(a.root/'normal_typing');log.observation(v);c=Controller(model.judge,log)
 row={'category':'normal_typing','phase':'verify','candidate':candidate,'source':str(source),'not_semantic_accuracy_estimate':True}
 try:
  value=c.inspect('verify',v,candidate,proposal);cross=c.check_current_focus(v)
  row.update(protocol_valid=True,result=value,focus_probe=cross['focus'],focus_agrees=cross['agrees'])
 except Exception:row.update(protocol_valid=False,error=traceback.format_exc())
 row['verifier_calls']=c.verifier_calls;row['model_calls_this_attempt']=c.verifier_calls;calls+=c.verifier_calls;rows.append(row)
 manifest.append({'category':'normal_typing','source':str(source),'phase':'verify','observation_id':'002-obs002','public_request_sha256':digest(canonical(v.data()))})
 (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2));(a.root/'results.json').write_text(json.dumps(rows,indent=2))
 summary={'phase':'completed','cases':14,'protocol_valid':sum(x['protocol_valid']for x in rows),'new_model_calls':calls,'reused_main_results':13,'reused_point_results':2,'parent':str(a.parent),'parent_results_sha256':digest((a.parent/'results.json').read_bytes()),'same_verifier_prompts_schema_backend_plan_and_actor':True,'scope':'incremental development regression; not 14 fresh model inferences or a Mirage-rate estimate','semantic_mirage':None}
 (a.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
