"""Collect public task descriptions, verifying private source seals remotely only."""
import base64
import hashlib
import json
import time

from remote_control import HERE, remote, save, sha

code = r'''
from pathlib import Path
import base64,hashlib,json
root=Path('/data/researcher/jev-defense-four-gpu-20261106/evaluation-source-preparation-20261109-01')
c=root/'collection';launch=json.loads((root/'once-only-launch.json').read_bytes())
assert not Path('/proc',str(launch['identity']['pid'])).exists()
receipt=json.loads((c/'receipt.json').read_bytes());assert receipt['status']=='complete'
assert receipt['tasks']==receipt['expected']==60
assert not(c/'failure.json').exists()
seal=json.loads((c/'seal.json').read_bytes())
for name,expected in seal.items():
 p=c/name;assert p.resolve().is_relative_to(c.resolve())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
public=json.loads((c/'public-task-catalog.json').read_bytes())
assert len(public['tasks'])==60 and public['private_answers_never_model_input']
allowed={'task_id','intent','image','sites','require_reset','source_member','source_config_sha256','private_evaluator_fields_exported','not_experiment_results'}
assert all(set(row)==allowed and row['private_evaluator_fields_exported']is False for row in public['tasks'])
private=list((c/'PRIVATE-evaluator-configs').glob('*.json'))
assert len(private)==60 and all(p.stat().st_mode&0o077==0 for p in private)
names=['public-task-catalog.json','receipt.json','seal.json','process.json','selection-before-archive-read.json']
files={name:base64.b64encode((c/name).read_bytes()).decode()for name in names}
print(json.dumps({'read_only':True,'models_GUI_scorer_calls':0,'remote_original_files_SHA_verified':len(seal),'private_source_files':len(private),
 'private_sources_not_exported':True,'files':files}))
'''
out, operation = remote('4090', code, 'collect-completed-public-catalog-only', timeout=55)
data=json.loads(out)
target=HERE/'public-task-source-collection'/str(time.time_ns());target.mkdir(parents=True,exist_ok=False)
for name,encoded in data.pop('files').items():
    assert '/'not in name and '\\'not in name
    (target/name).write_bytes(base64.b64decode(encoded))
save(target/'collection.json',dict(data,operation=str(operation),time=time.time()))
save(target/'local-public-seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
public=json.loads((target/'public-task-catalog.json').read_bytes())
print(json.dumps({'target':str(target),'public_catalog_sha256':sha(target/'public-task-catalog.json'),
    'summary':data,'tasks':[{'task_id':r['task_id'],'intent':r['intent'],'sites':r['sites'],'image':r['image'],'require_reset':r['require_reset']}for r in public['tasks']]},ensure_ascii=False))
