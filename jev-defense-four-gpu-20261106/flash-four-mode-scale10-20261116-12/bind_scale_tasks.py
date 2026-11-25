"""Freeze public, natively supported tasks without reading answer values."""
import json
import time
from pathlib import Path
from remote_util import HERE, remote, save, sha

CODE = r'''
import hashlib,json,os,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
root=Path('/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01/collection')
assert sha(root/'public-task-catalog.json')=='84a820b88f75676ca64477530b046aae27a680ddac7c066fd0c0e20586f1b65a'
assert sha(root/'seal.json')=='f10f49e4969be3c393754b8b710a314ccd71067270a6511f3ce4e6154d908e23'
seal=json.loads((root/'seal.json').read_bytes())
assert sha(root/'public-task-catalog.json')==seal['public-task-catalog.json']
catalog=json.loads((root/'public-task-catalog.json').read_bytes())
rows=[]
for task in sorted(catalog['tasks'],key=lambda v:int(v['task_id'])):
 p=root/'PRIVATE-evaluator-configs'/('classifieds_'+str(task['task_id'])+'.PRIVATE.json')
 h=sha(p);assert h==task['source_config_sha256']==seal[p.relative_to(root).as_posix()]
 cfg=json.loads(p.read_bytes())
 assert all(cfg[k]==task[k]for k in ['intent','image','sites','require_reset'])
 # Only capability identifiers are inspected. Reference URLs/answers stay remote.
 types=cfg['eval']['eval_types']
 reasons=[]
 if task['task_id']in[114,125]:reasons.append('completed_parent_task')
 if cfg['image']is not None:reasons.append('native_adapter_text_only')
 if cfg['require_reset']is not False:reasons.append('reset_not_authorized')
 if cfg['sites']!=['classifieds']:reasons.append('unsupported_site')
 if types!=['url_match']:reasons.append('unsupported_native_scorer_type')
 rows.append({'task_id':task['task_id'],'intent':task['intent'],'image':task['image'],
  'sites':task['sites'],'require_reset':task['require_reset'],'source_member':task['source_member'],
  'source_config_sha256':h,'original_private_path':str(p),'original_private_SHA':h,
  'public_intent_SHA':hashlib.sha256(cfg['intent'].encode()).hexdigest(),
  'intent_exactly_matches_preselected_public_source':True,'start_url':cfg['start_url'],
  'start_url_SHA':hashlib.sha256(cfg['start_url'].encode()).hexdigest(),
  'eval_types':types,'native_scorer_type':'url_match'if types==['url_match']else None,
  'eligible':not reasons,'exclusion_reasons':reasons,
  'private_scorer_answers_or_reference_urls_exported':False})
print(json.dumps({'time':time.time(),'uid':os.getuid(),'rows':rows,'catalog_sha256':sha(root/'public-task-catalog.json'),
 'collection_seal_sha256':sha(root/'seal.json'),'private_answers_inspected_or_exported':False,
 'new_model_GUI_scorer_calls':0}))
'''

def main():
    assert not (HERE/'task-selection-current.json').exists()
    raw,op=remote('4090',CODE,'structural-native-task-binding-no-private-answers')
    value=json.loads(raw)
    eligible=[v for v in value['rows']if v['eligible']]
    assert len(eligible)>=8
    root=HERE/('task-selection-'+str(time.time_ns()));root.mkdir()
    save(root/'structural-bindings.json',{'operation':str(op),'result':value})
    selection={'rule':'ascending numeric public task ID; exclude completed T114/T125; no task image/reset; classifieds/url_match only; no outcome/reference-answer selection',
      'prior_success_per_condition':2,'target_success_per_condition':10,'new_task_ids':[v['task_id']for v in eligible[:8]],
      'reserve_task_ids':[v['task_id']for v in eligible[8:]],'all_eligible_task_ids':[v['task_id']for v in eligible],
      'initial_new_trajectories':40,'conditions':['buttons_only','silent_drop','blank_replace','stale_replace','clean_control'],
      'reserve_policy':'After auditing initial group, use next unused task in this frozen order for deficient modes plus a clean control; preserve all prior failures and untriggered terminals; no terminal rerun.',
      'not_random_or_fully_blind':True,'private_answers_not_inspected':True,'frozen_before_new_inference':True}
    save(root/'selection.json',selection)
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    save(HERE/'task-selection-current.json',{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps(selection,ensure_ascii=False))

if __name__=='__main__':main()
