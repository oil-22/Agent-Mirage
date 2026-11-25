"""Link a metadata-path correction and verify32-track source/budget boundaries."""
import ast
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
source=HERE/'prepared-source';target=HERE/'prepared-source-linked02'
assert not target.exists()
for name,expected in read(source/'seal.json').items():assert sha(source/name)==expected,name
target.mkdir()
for p in source.iterdir():
    if p.is_file()and p.name!='seal.json':
        with(target/p.name).open('xb')as stream:stream.write(p.read_bytes())
runner=target/'run_independent_gui.py'
text=runner.read_text(encoding='utf8')
old="['run_single_evidence_gui.py','gui_transport.py','protocol.py','complete_actor_history.py'"
new="['run_independent_gui.py','gui_transport.py','protocol.py','complete_actor_history.py'"
assert text.count(old)==1
runner.write_text(text.replace(old,new),encoding='utf8')
for path in target.glob('*.py'):ast.parse(path.read_text(encoding='utf8'))
plan=read(target/'plan.json');queue=plan['queue']
assert len(queue)==32 and len({row['run_id']for row in queue})==32
assert sorted({row['task_id']for row in queue})==[0,3,17,58,89,94,114,125]
orders={False:0,True:0}
for task in sorted({row['task_id']for row in queue}):
    for condition in ['clean','stale_replace']:
        pair=[row for row in queue if row['task_id']==task and row['condition']==condition]
        assert len(pair)==2 and {row['observer_enabled']for row in pair}=={False,True}
        assert all(row['arm']=='joint'for row in pair)
        orders[pair[0]['observer_enabled']]+=1
assert orders=={False:8,True:8}
lim=plan['limits']
assert lim['max_actor_calls']==70 and lim['max_verifier_calls']==140
assert lim['max_recaptures_per_decision']==2 and lim['max_regenerations_per_decision']==2
old_protocol=HERE.parent/'full-gui-bounded-evidence-20261109-03/runtime-package/protocol.py'
assert sha(target/'protocol.py')==sha(old_protocol)
result={'time':time.time(),'source_preparation_only':True,'launch_ready':False,
        'previous_prepared_source_seal_sha256':sha(source/'seal.json'),
        'metadata_path_repair':'Implementation receipt names actual run_independent_gui.py instead of old runner basename; old source seal kept.',
        'native_tasks':8,'tracks':32,'matched_pairs':16,
        'first_arm_orders':{'noaux':orders[False],'aux':orders[True]},
        'complete_accepted_actor_history_helper_sha256':sha(target/'complete_actor_history.py'),
        'unchanged_protocol_source_sha256':sha(target/'protocol.py'),
        'limits_verified':lim,'format_retry_policy':'Original strict Controller default1 retained; no extra retry added.',
        'no_old_task112_only_queue_or_runtime_resumed':True,
        'no_model_GPU_GUI_scorer_calls':True,
        'native_runtime_live_admission_not_proven_by_source_checks':True,
        'remaining_admission':plan['remaining_admission']}
(target/'preparation-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(target/'seal.json').write_text(json.dumps({p.name:sha(p)for p in target.iterdir()if p.is_file()},indent=2)+'\n',encoding='utf8')
print(json.dumps({'prepared':str(target),'receipt_sha256':sha(target/'preparation-receipt.json'),'seal_sha256':sha(target/'seal.json'),'tracks':32,'launch_ready':False}))
