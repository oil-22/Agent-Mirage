"""Read-only paired trace comparison; equality is not a Mirage label."""
import json
import time
from control import HERE, R4090, remote, save, sha
from capture_live_evidence import COMMON

code = 'ROOT=' + repr(R4090) + '\n' + COMMON + r'''
r=Path(ROOT);out={'time':time.time(),'new_model_GUI_calls':0,'runs':[]}
for attempt in sorted((r/'batch/runs').glob('*/attempt-*')):
 protocol=json.loads((attempt/'protocol.json').read_bytes());run=protocol['run']
 proof,events=chain(attempt/'controller/events.jsonl')
 requests=[v['data']for v in events if v['kind']=='actual_actor_request']
 replies={v['data']['request_id']:v['data']for v in events if v['kind']=='actual_actor_reply'}
 forwarded=[v['data']for v in events if v['kind']=='main_image_forwarded']
 ledger={v['data']['step']:v['data']for v in events if v['kind']=='PRIVATE_delivery_ledger'}
 actions={v['data']['step']:v['data']for v in events if v['kind']=='native_environment_action'}
 closed=[]
 for i,request in enumerate(requests,1):
  reply=replies.get(request['request_id'])
  if reply is None:continue
  assert i<=len(forwarded) and i in ledger
  l=ledger[i];f=forwarded[i-1];a=actions.get(i)
  assert f['image_sha256']==l['delivered_sha256']
  closed.append({'step':i,'body_sha256':request['body_sha256'],'candidate_text_sha256':reply['text_sha256'],'delivered_PNG_sha256':f['image_sha256'],'actually_captured_PNG_sha256':l['captured_sha256'],'native_environment_action':a['payload']if a else None,'post_execution_PNG_sha256':a['current_capture_sha256']if a else None,'gate_request_id':f['gate_request_id'],'actor_request_id':request['request_id']})
 terminal=json.loads((attempt/'terminal.json').read_bytes())if(attempt/'terminal.json').exists()and(attempt/'seal.json').exists()else None
 out['runs'].append({'run':run,'attempt':str(attempt),'protocol_sha256':sha(attempt/'protocol.json'),'chain':proof,'closed_actor_prefix':closed,'sealed_terminal':terminal is not None,'terminal_sha256':sha(attempt/'terminal.json')if terminal else None,'terminal_summary':{k:terminal.get(k)for k in ['outcome','actor_calls','environment_actions','official_reward','injection_fired','infrastructure_failure']}if terminal else None})
print(json.dumps(out))
'''
raw, operation = remote('4090', code, 'paired-trace-equality-readonly')
value = json.loads(raw)
plan = json.loads((HERE / 'package/plan.json').read_bytes())
by_run = {v['run']['run_id']: v for v in value['runs']}
pairs = []
for task in plan['tasks']:
    if task['task_id'] == 0:
        continue
    for condition in ['clean', 'stale_replace']:
        key = 'flash14-T%03d-%s-' % (task['task_id'], condition)
        baseline = by_run.get(key + 'baseline')
        gate = by_run.get(key + 'gate')
        a = baseline['closed_actor_prefix'] if baseline else []
        b = gate['closed_actor_prefix'] if gate else []
        fields = ['body_sha256', 'candidate_text_sha256', 'delivered_PNG_sha256',
                  'actually_captured_PNG_sha256', 'native_environment_action', 'post_execution_PNG_sha256']
        compared = []
        for left, right in zip(a, b):
            assert left['step'] == right['step']
            compared.append({'step': left['step'], 'equal': {k: left[k] == right[k] for k in fields}})
        complete = bool(baseline and gate and baseline['sealed_terminal'] and gate['sealed_terminal'])
        first_difference = next((v for v in compared if not all(v['equal'].values())), None)
        same_length = len(a) == len(b)
        pairs.append({'task_id': task['task_id'], 'condition': condition,
                      'baseline_closed': len(a), 'gate_closed': len(b), 'compared_decisions': len(compared),
                      'both_sealed_terminals': complete, 'same_closed_length': same_length,
                      'all_compared_fields_equal': all(all(v['equal'].values()) for v in compared) if compared else None,
                      'complete_trace_equal': bool(complete and same_length and compared and first_difference is None),
                      'first_difference': first_difference,
                      'baseline_terminal': baseline['terminal_summary'] if baseline else None,
                      'gate_terminal': gate['terminal_summary'] if gate else None,
                      'comparisons': compared})
dest = HERE / ('pair-trace-equivalence-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'source-traces.json', value)
save(dest / 'comparison.json', {
    'time': time.time(), 'source_operation': str(operation), 'source_sha256': sha(dest / 'source-traces.json'),
    'planned_pairs': 14, 'pairs': pairs,
    'observations': 'Trace/hash equality uses checked controller chains. It is not independent current GPU tensor verification, semantic labeling, or an effectiveness estimate. Pending/unattempted prefixes are not equivalent completed trials.',
    'T000_unpaired_excluded': True, 'native_contract_failure_is_not_Mirage_zero': True,
    'semantic_review_labels_used_as_truth': False, 'Mirage_reduction': None, 'new_model_GUI_calls': 0})
save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
print(json.dumps({'comparison': str(dest), 'completed_pairs': sum(p['both_sealed_terminals'] for p in pairs),
                  'whole_equal_pairs': sum(p['complete_trace_equal'] for p in pairs),
                  'partial_paired_decisions': sum(p['compared_decisions'] for p in pairs if not p['both_sealed_terminals']),
                  'Mirage_reduction': None}))
