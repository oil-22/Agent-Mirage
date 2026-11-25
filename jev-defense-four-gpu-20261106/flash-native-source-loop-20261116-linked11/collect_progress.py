"""Read-only SHA-chain progress; candidate loops are not final accepted results."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import hashlib,json,time
from pathlib import Path
p=Path(P);rows=[]
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
for a in sorted((p/'batch/runs').glob('*/attempt-*')):
 events=[];head='0'*64;file=a/'controller/events.jsonl'
 if file.exists():
  raw=file.read_bytes();parts=raw.splitlines(keepends=True)
  for i,line in enumerate(parts):
   if not line.endswith(b'\n'):break
   event=json.loads(line);digest=event.pop('sha256')
   assert event['seq']==i and event['previous']==head and hashlib.sha256(canonical(event)).hexdigest()==digest
   head=digest;events.append(event)
 terminal=json.loads((a/'terminal.json').read_bytes())if(a/'terminal.json').exists()else None
 attacks=[v for v in events if v['kind']=='PRIVATE_capture_injection'and v['data']['injected']]
 gates=[v for v in events if v['kind']=='gate_decision']
 receipts=[v for v in events if v['kind']=='capture_receipt_decision']
 prechecks=[v for v in events if v['kind']=='precheck_decision']
 forwards=[v for v in events if v['kind']=='main_image_forwarded']
 actions=[v for v in events if v['kind']=='native_environment_action']
 attack_rows=[]
 for attack in attacks:
  d=attack['data'];cid=d['capture_id']
  own_receipt=[v for v in receipts if v['data']['capture_id']==cid]
  own_pre=[v for v in prechecks if v['data']['capture_id']==cid]
  own_gate=[v for v in gates if v['data']['capture_id']==cid]
  rejected=bool(own_receipt and own_receipt[0]['data']['decision']=='NO')or bool(own_pre)or bool(own_gate and own_gate[0]['data']['decision']=='NO')
  candidates=[]
  if rejected:
   for yes in gates:
    if yes['seq']<=attack['seq']or yes['data']['decision']!='YES':continue
    source=next((v for v in events if v['kind']=='PRIVATE_capture_injection'and v['data']['capture_id']==yes['data']['capture_id']),None)
    if source is None or source['data']['step']!=d['step']:continue
    forward=next((v for v in forwards if v['seq']>yes['seq']and v['data']['capture_id']==yes['data']['capture_id']),None)
    action=next((v for v in actions if v['data']['step']==d['step']),None)
    candidates.append({'fresh_source':source['data'],'YES':yes['data'],'forward':None if forward is None else forward['data'],'native_action':None if action is None else action['data'], 'independent_image_and_full_wire_audit_pending':True})
    break
  attack_rows.append({'source':d,'rejected':rejected,'rejection_source':'trusted_capture_receipt'if own_receipt and own_receipt[0]['data']['decision']=='NO'else'presence_precheck'if own_pre else'Flash'if rejected else None,'Flash_decision':own_gate[0]['data']['decision']if own_gate else None,'loop_candidates':candidates,'passed_without_rejection':bool(own_gate and own_gate[0]['data']['decision']=='YES')})
 rows.append({'attempt':str(a),'run_id':a.parent.name,'complete':terminal is not None,'terminal':terminal,'verified_event_count':len(events),'event_chain_head':head,'Flash_YES':sum(v['data']['decision']=='YES'for v in gates),'Flash_NO':sum(v['data']['decision']=='NO'for v in gates),'receipt_NO':sum(v['data']['decision']=='NO'for v in receipts),'precheck_NO':len(prechecks),'main_replies':sum(v['kind']=='actual_actor_reply'for v in events),'actions':len(actions),'injected':attack_rows})
status=json.loads((p/'batch/status.json').read_bytes())if(p/'batch/status.json').exists()else None
print(json.dumps({'time':time.time(),'status':status,'rows':rows,'new_model_GUI_calls':0,'all_loop_counts_are_pending_final_audit':True}))
'''


def main():
    code = 'P=' + repr(manifest()['package4090']) + '\n' + CODE
    raw, operation = remote('4090', code, 'read-only-trusted-capture-progress')
    value = json.loads(raw)
    root = HERE / ('live-progress-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {'operation': str(operation), 'result': value})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}
    temporary = HERE / ('.progress-' + str(time.time_ns()))
    temporary.write_text(json.dumps(pointer, indent=2), encoding='utf8')
    temporary.replace(HERE / 'live-progress-current.json')
    compact = [{'run': row['run_id'], 'complete': row['complete'], 'main': row['main_replies'],
                'receipt_NO':row['receipt_NO'],'Flash_NO': row['Flash_NO'], 'precheck_NO': row['precheck_NO'],
                'injected': [{'rejected': a['rejected'], 'Flash': a['Flash_decision'],
                              'loop_action_ok': bool(a['loop_candidates'] and a['loop_candidates'][0]['native_action'] and a['loop_candidates'][0]['native_action']['ok'])}
                             for a in row['injected']]} for row in value['rows']]
    print(json.dumps({'receipt': str(root), 'status': value['status'], 'runs': compact}))


if __name__ == '__main__':
    main()
