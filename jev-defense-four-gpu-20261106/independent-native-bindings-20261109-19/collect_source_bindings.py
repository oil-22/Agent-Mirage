"""Bind the already selected eight independent tasks without viewing outcomes.

Private scorer answers/URLs remain remote and never become model inputs.
This script has no browser/model/scorer operation and cannot start a queue.
"""
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha


def main():
    plan=BASE/'independent-evaluation-preparation-20261109-04/prospective-plan.json'
    value=json.loads(plan.read_bytes())
    selected=[{k:row[k]for k in ['task_id','intent','source_config_sha256','source_member']}for row in value['selected_tasks']]
    assert [row['task_id']for row in selected]==[0,3,17,58,89,94,114,125]
    code='SELECTED='+repr(selected)+'\nPLAN_SHA='+repr(sha(plan))+'\n'+r'''
from pathlib import Path
import ast,hashlib,json,os,subprocess,time
assert os.getuid()==1015
r=Path('/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01/collection')
runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=json.loads((r/'seal.json').read_bytes());catalog=json.loads((r/'public-task-catalog.json').read_bytes())
public={row['task_id']:row for row in catalog['tasks']}
rows=[]
for selected in SELECTED:
 ident=selected['task_id'];p=r/'PRIVATE-evaluator-configs'/('classifieds_'+str(ident)+'.PRIVATE.json')
 assert p.is_file() and p.stat().st_uid==1015 and p.stat().st_mode&0o077==0
 assert sha(p)==selected['source_config_sha256']==public[ident]['source_config_sha256']==seal[p.relative_to(r).as_posix()]
 v=json.loads(p.read_bytes());assert v['intent']==selected['intent']==public[ident]['intent']
 assert v['image']is None and v['sites']==['classifieds'] and v['require_reset']is False
 assert v['eval']['eval_types']==['url_match'] and isinstance(v['start_url'],str)
 # Export the public initial URL only. No evaluation answer or reference URL.
 rows.append({'task_id':ident,'original_private_path':str(p),'original_private_SHA':sha(p),
  'source_member':selected['source_member'],'public_intent_SHA':hashlib.sha256(v['intent'].encode()).hexdigest(),
  'intent_exactly_matches_preselected_public_source':True,'start_url':v['start_url'],
  'start_url_SHA':hashlib.sha256(v['start_url'].encode()).hexdigest(),'image':None,
  'require_reset':False,'sites':['classifieds'],'native_scorer_type':'url_match',
  'evaluation_keys_only':sorted(v['eval']),'private_permissions_verified':True,
  'private_scorer_answers_or_reference_urls_exported':False})
source=runtime/'native/run_reddit_internvl_smoke.py'
tree=ast.parse(source.read_text());native={}
for node in tree.body:
 if isinstance(node,(ast.FunctionDef,ast.Assign)):
  name=node.name if isinstance(node,ast.FunctionDef)else(next((x.id for x in node.targets if isinstance(x,ast.Name)),None))
  if name in ['SYSTEM','parse','action','png']:
   native[name]=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
assert set(native)=={'SYSTEM','parse','action','png'}
evaluator=runtime/'upstream/evaluation_harness/evaluators.py'
assert sha(evaluator)=='00419191831d8a4d5260b7e742b964992acb95c4846864f46b7017ef8ca89f34'
actor=Path('/data/researcher/jev-defense-validation-20261103/native-vwa-request.recovered.json')
template=json.loads(actor.read_bytes());assert template['max_tokens']==2048 and template['temperature']==0
assert template['chat_template_kwargs']=={'enable_thinking':False}
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
containers=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
site=[]
for c,expected in zip(containers,ids):
 assert c['Id']==expected and c['Config']['Labels']['owner']=='whz-qwen27-vwa' and c['State']['Running']
 site.append({'id':c['Id'],'owner':c['Config']['Labels']['owner'],'running':True,'image_id':c['Image'],
              'port_bindings':c['HostConfig']['PortBindings'],'volumes':[m.get('Name')for m in c['Mounts']if m.get('Name')]})
assert site[0]['port_bindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert 'qwen27_vwa_db_data'in site[1]['volumes']
print(json.dumps({'time':time.time(),'read_only':True,'prospective_plan_SHA':PLAN_SHA,'tasks':rows,
 'native_actor_template_sha256':sha(actor),'native_parser_source':str(source),'native_source_SHA':sha(source),'native_AST_SHA':native,
 'native_URL_scorer_source_SHA':sha(evaluator),'dedicated_site':site,
 'new_model_GPU_browser_agent_scorer_paid_calls':0,'site_reset_or_fixture_import':False,
 'private_scorer_sources_not_exported_or_sent_to_models':True,'task_outcomes_or_reference_answers_not_inspected':True,
 'same_live_initial_capture_and_recapture_done':False,'native_scorer_transport_exercised':False,
 'task_browser_lease_acquired':False,'complete_GUI_launcher_ready':False}))
'''
    output,operation=remote('4090',code,'bind-eight-prospective-native-task-sources-no-outcomes',timeout=55)
    evidence=json.loads(output)
    target=HERE/('source-bindings-'+str(time.time_ns()));target.mkdir()
    evidence['operation']=str(operation)
    save(target/'receipt.json',evidence)
    save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
    print(json.dumps({'evidence':str(target),'receipt_SHA':sha(target/'receipt.json'),'task_ids':[r['task_id']for r in evidence['tasks']],
                      'source_bindings_complete':True,'live_initial_scorer_transport_and_site_lease_still_pending':True,'new_model_GUI_calls':0},ensure_ascii=False))


if __name__=='__main__':main()
