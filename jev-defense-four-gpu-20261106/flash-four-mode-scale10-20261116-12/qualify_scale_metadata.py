"""Check only new task/count/launch metadata; reuse unchanged algorithm controls."""
import ast
import json
import time
from pathlib import Path
from remote_util import HERE,save,sha

def main():
    assert not(HERE/'CPU-routing-current.json').exists()
    prep=json.loads((HERE/'preparation-current.json').read_bytes());p=Path(prep['package'])
    assert sha(p/'manifest.json')==prep['manifest_sha256']
    m=json.loads((p/'manifest.json').read_bytes())
    for n,h in m['files'].items():assert sha(p/n)==h,n
    plan=json.loads((p/'plan.json').read_bytes())
    selection=json.loads((p/'task-selection.json').read_bytes())
    assert len(m['remaining_queue'])==m['trajectories']==plan['expected_trajectories']==40
    assert plan['queue']==m['remaining_queue']
    assert [t['task_id']for t in plan['tasks']]==selection['new_task_ids']==[0,3,17,58,89,94,112,131]
    assert len({r['run_id']for r in plan['queue']})==40
    for c in selection['conditions']:assert sum(r['condition']==c for r in plan['queue'])==8
    assert len({(r['task_id'],r['condition'])for r in plan['queue']})==40
    bindings=json.loads((p/'native-bindings-public.json').read_bytes())
    assert bindings['prospective_plan_SHA']==sha(p/'plan.json')
    assert all(r['eval_types']==['url_match']and r['eligible']and r['image']is None and r['require_reset']is False for r in bindings['tasks'])
    assert m['Flash_contract_sha256']==sha(p/'flash/gate-contract.json')==plan['single_image_quality_contract_sha256']
    old=HERE.parent/'flash-native-source-loop-20261116-linked11'
    reused=[]
    for name in ['CPU-routing-current.json','CPU-source-current.json']:
        q=json.loads((old/name).read_bytes());assert q['passed'];assert sha(Path(q['root'])/'seal.json')==q['seal_sha256']
        reused.append({'pointer':str(old/name),'pointer_sha256':sha(old/name),'proof':q,'new_control_executions':0})
    invariant=json.loads((Path(prep['root'])/'source-invariance.json').read_bytes())
    for n,h in invariant['unchanged_runtime_files'].items():assert sha(p/n)==h
    for q in HERE.glob('*.py'):ast.parse(q.read_text('utf8'))
    from audit_completed_group_bound_reuse import readers
    readers()
    assert 'new_trusted_capture_protocol_authorized'in json.loads((p/'user-current-authorization.json').read_bytes())
    root=HERE/('cpu-metadata-qualification-'+str(time.time_ns()));root.mkdir()
    save(root/'result.json',{'passed':True,'manifest_sha256':prep['manifest_sha256'],
        'new_metadata_checks':['40 unique task/condition pairs','8 per condition','native structural capability and public source hash','fresh manifest/identifiers/authorization','same Flash prompt and inference/capture/controller source','audit readers compile'],
        'reused_routing_and_source_qualifications':reused,'algorithm_control_reexecutions':0,'new_model_GUI_calls':0})
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(HERE/'CPU-routing-current.json',{'root':str(root),'seal_sha256':sha(root/'seal.json'),'passed':True,'manifest_sha256':prep['manifest_sha256'],'qualification_type':'metadata checks and source-identical qualification reuse'})
    print(json.dumps({'passed':True,'root':str(root),'trajectories':40,'new_model_GUI_calls':0}))

if __name__=='__main__':main()
