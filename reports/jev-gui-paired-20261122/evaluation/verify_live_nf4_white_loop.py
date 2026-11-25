"""Record a live decision-two loop for missing, white, or in-transit stale input."""

import argparse
import json
from pathlib import Path
import sys
import time

from collect import HERE, EXPERIMENT, read, save, sha
from link import verify
sys.path.insert(0,str(EXPERIMENT/'quantized-continuation-20261123'))
from resume_frozen_suffix import setup, control


GUI=r'''
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import os
p=Path(ROOT)
assert os.getuid()==1015 and sha(p/'manifest.json')==EXPECTED
status=read(p/'batch/status.json')
assert status['phase']=='running' and status['run_id']==CASE and status['step']>2
attempt,=(p/'batch/runs'/CASE).glob('attempt-*')
ctl,head=journal(attempt/'controller/events.jsonl',live=True)
src,source_head=journal(attempt/'trusted-source/events.jsonl',live=True,source=True)
def one(rows, **fields):
    value,=[r for r in rows if all(r.get(k)==v for k,v in fields.items())]
    return value
init=one(data(ctl,'PRIVATE_capture_injection'),step=2,injected=True,capture_kind='initial')
decs=data(ctl,'capture_receipt_decision')
assert init['condition']==CONDITION and init['captured_sha256']!=init['delivered_sha256']
if CONDITION=='silent_drop':
    assert init['delivered_file'] is None and init['delivered_sha256'] is None
    stage='precheck_decision'
    assert not [e for e in decs if e['capture_id']==init['capture_id']]
    no=one(data(ctl,stage),capture_id=init['capture_id'],decision='NO',reason='missing_image')
else:
    assert CONDITION in {'blank_replace','stale_replace'}
    stage='capture_receipt_decision'
    no=one(decs,capture_id=init['capture_id'],decision='NO',reason='capture_bytes_replaced')
previous_original=None
if CONDITION=='stale_replace':
    previous=one(data(ctl,'PRIVATE_capture_injection'),step=1,injected=False,capture_kind='initial')
    previous_original=previous['captured_sha256']
    assert sha(attempt/previous['raw_file'])==sha(attempt/previous['delivered_file'])==previous_original
    assert init['delivered_sha256']==previous['delivered_sha256']==previous_original!=init['captured_sha256']
    prior_action=one(data(ctl,'native_environment_action'),step=1)
    assert prior_action['ok']
assert no['not_a_model_NO'] and not no['Flash_called']
assert not [e for e in data(ctl,'gate_decision') if e['capture_id']==init['capture_id']]
one(data(ctl,'recapture_requested'),from_capture_id=init['capture_id'])
submit=one(data(ctl,'actor_submit_timing'),step=2)
recap=one(data(ctl,'PRIVATE_capture_injection'),step=2,capture_kind='recapture',capture_id=submit['capture_id'])
assert recap['captured_sha256']==recap['delivered_sha256']==submit['image_sha256'] and not recap['injected']
binding=read(attempt/'trusted-source/ready.json')
assert binding['identity']['uid']==1015 and not binding['fixture']
assert sha(p/'capture_source.py')==binding['source_code_sha256']
pk=bytes.fromhex(binding['public_key']); assert hx(pk)==binding['key_id']
pub=Ed25519PublicKey.from_public_bytes(pk)
receipts={}
for row in (init,recap):
    assert sha(attempt/row['raw_file'])==row['captured_sha256']
    if row['delivered_file'] is not None:
        assert sha(attempt/row['delivered_file'])==row['delivered_sha256']
    source,=[q for q in data(src,'actual_native_capture_signed') if q['receipt']['capture_id']==row['capture_id']]
    rec=source['receipt']
    assert sha(Path(source['original_file']))==rec['image_sha256']==row['captured_sha256']
    prefix=attempt/'capture-deliveries'/f"{row['capture_index']:04d}"
    assert read(Path(str(prefix)+'-signed-receipt.json'))==rec
    challenge=read(Path(str(prefix)+'-expected-challenge.json'))
    assert all(rec[k]==challenge[k] for k in ('challenge','environment_id','action_sequence'))
    pub.verify(bytes.fromhex(rec['signature']),canonical({k:v for k,v in rec.items() if k!='signature'}))
    receipts[row['capture_kind']]=rec
a,b=receipts['initial'],receipts['recapture']
assert a['capture_index']<b['capture_index'] and a['challenge']!=b['challenge']
assert all(a[k]==b[k]==binding[k] for k in ('session_id','environment_id'))
assert a['action_sequence']==b['action_sequence']
faults=[e for e in data(src,'PRIVATE_unsigned_native_fault_rendered') if e['preceding_capture_id']==init['capture_id']]
if CONDITION=='blank_replace':
    fault,=faults
    assert fault['signature_issued'] is False and fault['name']==CONDITION
    assert fault['delivered_sha256']==init['delivered_sha256']
else:
    assert not faults
one(decs,capture_id=recap['capture_id'],decision='YES')
yes=one(data(ctl,'gate_decision'),capture_id=recap['capture_id'],decision='YES')
forwarded=one(data(ctl,'main_image_forwarded'),capture_id=recap['capture_id'])
assert yes['image_sha256']==forwarded['image_sha256']==recap['delivered_sha256']
assert forwarded['gate_request_id']==yes['request_id'] and not forwarded['extra_auxiliary_text_in_main_prompt']
observations=[i for i,row in enumerate(ctl) if row['kind']=='observation_started_timing' and row['data']['step']==2]
i,=observations
until=next(j for j in range(i+1,len(ctl)) if ctl[j]['kind']=='observation_finished_timing')
q,=data(ctl[i:until],'actual_actor_request')
r,=data(ctl[i:until],'actual_actor_reply')
action,=data(ctl[i:until],'native_environment_action')
assert q['request_id']==r['request_id'] and q['history_messages']==4
assert action['step']==2 and action['ok']
source_action=one(data(src,'native_action_executed'),sequence=b['action_sequence']+1)
assert source_action['ok']
print(json.dumps({'run':CASE,'condition':CONDITION,'step':2,'choice':stage,'rejection_reason':no['reason'],
    'altered_initial_delivered_sha256':init['delivered_sha256'],
    **({'white_delivered_sha256':init['delivered_sha256']} if CONDITION=='blank_replace' else {}),
    **({'previous_original_sha256':previous_original,'fault_boundary':'in_transit_replacement'}
       if CONDITION=='stale_replace' else {}),
    'signed_initial_sha256':init['captured_sha256'],'recovery_delivered_sha256':recap['delivered_sha256'],
    'normal_recapture_path':str(attempt/recap['delivered_file']),'same_seq':b['action_sequence'],
    'new_signed_native_capture':True,'Flash_yes_request_id':yes['request_id'],
    'main_request_id':q['request_id'],'main_body_sha256':q['body_sha256'],'main_reply_sha256':r['text_sha256'],
    'native_action_type':action['payload']['type'],'native_execution_returned_true':True,
    'controller_head':head,'source_head':source_head}))
'''


MODEL=r'''
import os
p=Path(ROOT)
assert os.getuid()==1033 and sha(p/'manifest.json')==EXPECTED
result=model_extract(p,Path(OUTPUT),read(p/'plan.json'))
rid=GUI_PROOF['main_request_id']; m=result['requests'][rid]
assert m['run']==CASE and m['step']==2 and m['actual_forward'] and m['forward_calls'] >= 1 and m['natural_EOS']
assert m['tensor_raw_bytes_fully_audited'] and m['images_all_history']==2
assert m['current_image_sha256']==GUI_PROOF['recovery_delivered_sha256']
assert m['body_sha256']==GUI_PROOF['main_body_sha256'] and m['reply_sha256']==GUI_PROOF['main_reply_sha256']
f=result['flash'][GUI_PROOF['Flash_yes_request_id']]
assert f['run']==CASE and f['decision']=='YES' and f['image_sha256']==m['current_image_sha256']
print(json.dumps({'main_request_id':rid,'actual_forward_calls':m['forward_calls'],'natural_EOS':True,
  'primary_journal_head':result['primary_chain_head'],'Flash_journal_head':result['flash_chain_head'],
  'main_request_seal_sha256':m['seal_sha256'],'Flash_reply_seal_sha256':f['seal_sha256'],
  'linked_recovery_image_sha256':m['current_image_sha256'],'raw_forward_tensor_bytes_rehashed_at_recovery':True}))
'''


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('run', help='Matching decision-two on arm currently running.')
    run = args.parse_args().run
    setup()
    queue = read(control.PACKAGE/'plan.json')['queue']
    slot, = (q for q in queue if q['run_id'] == run)
    assert slot['condition'] in {'blank_replace','silent_drop','stale_replace'} and slot['arm'] == 'on'
    source=(HERE/'extract_on_host.py').read_text(encoding='utf-8')
    load="__name__='read_only_evidence_library'\n"+source+'\n'
    gui=control.remote('4090',control.prefix('4090')+f'CASE={run!r}\nCONDITION={slot["condition"]!r}\n'+load+GUI,
                       'verify-live-rejection-and-recapture')
    settings=(f'CASE={run!r}\nGUI_PROOF={gui["result"]!r}\nOWNED_RUNS={[q["run_id"] for q in queue]!r}\n'
              f'TARGET_RUNS={[run]!r}\nOLD_PRIMARY_HEAD=None\nOLD_FLASH_HEAD=None\n')
    model=control.remote('3090',control.prefix('3090')+settings+load+MODEL,'verify-live-recovery-actual-forward',timeout=85)
    dst=HERE/'live-observation-evidence'/str(time.time_ns()); dst.mkdir(parents=True,exist_ok=False)
    evidence={}
    for host,r in [('GUI',gui),('model',model)]:
        operation=Path(r['operation']);verify(operation)
        evidence[host]={**r,'operation_seal_sha256':sha(operation/'seal.json')}
    save(dst/'observation.json',{**evidence,'no_new_GPU_model_GUI_or_score_calls':True,
        'provisional_until_full_trajectory_seal':True,'no_official_trajectory_score_claim':True})
    save(dst/'seal.json',{'observation.json':sha(dst/'observation.json')})
    print(json.dumps({'receipt':str(dst),**{k:v['result'] for k,v in evidence.items()}},ensure_ascii=True))


if __name__=='__main__':main()
