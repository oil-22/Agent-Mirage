"""Freeze outcome-independent engineering cohort, not a powered main experiment."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
source=R.parent/'qwen35-9b-pilot-20261019/plan320.json';raw=source.read_bytes();old=json.loads(raw)
H=lambda b:hashlib.sha256(b).hexdigest()
tasks={}
for dataset,items in old['tasks'].items():
 def key(t):return H(('defense27-pilot-seed42:'+dataset+':'+str(t.get('pilot_task_id',t.get('id',t.get('task_id'))))).encode())
 tasks[dataset]=[min(items,key=key)]
arms=['baseline','pre_only','post_only','joint'];conditions=['clean']+old['conditions'];queue=[]
for dataset,items in tasks.items():
 for task in items:
  ident=str(task.get('pilot_task_id',task.get('id',task.get('task_id'))))
  for condition in conditions:
   order=sorted(arms,key=lambda arm:H(f'defense27-arm-order42:{dataset}:{ident}:{condition}:{arm}'.encode()))
   for arm in order:
    queue.append(dict(dataset=dataset,task=task,condition=condition,arm=arm,run_id=f'{dataset}--{ident}--{condition}--{arm}'))
plan=dict(experiment='27B defense engineering pilot',model='/data/llms/Qwen3.8-27B',architecture='Qwen3_5ForConditionalGeneration',dtype='BF16',backend='sdpa',quantization=False,source_task_pool=str(source),source_sha256=H(raw),selection='Minimum SHA256(defense27-pilot-seed42:dataset:identity); no Mirage or task-success labels',tasks=tasks,arms=arms,conditions=conditions,expected_runs=len(queue),queue=queue,max_environment_actions=50,history='complete native text history; no truncation; corrections appended explicitly',image='original native image processing, no new resize',limits=dict(max_actor_calls=70,max_verifier_calls=140,max_recaptures_per_decision=2,max_regenerations_per_decision=2,wait_seconds=[0.5,1.0]),actor_protocol='must bind exact native27B request/template/parser before GUI launch; generic verifier is not the baseline actor',semantic_labels='independent manual review; detector flags are not labels',status='prepared_not_launched',power='4 task instances, engineering pilot only; no claim of significant reduction',live_environment_gates='isolated contexts and no concurrent shared mutable task state; no resets of active experiments')
assert len(queue)==80 and len({q['run_id']for q in queue})==80
out=R/'plan80.json';data=json.dumps(plan,ensure_ascii=False,indent=2).encode()
if out.exists():assert out.read_bytes()==data
else:out.write_bytes(data)
print(json.dumps({'expected_runs':len(queue),'selected':tasks,'sha256':H(data)},ensure_ascii=False,indent=2))
