"""Compare recorded recovery-arm decisions with the sealed same-task clean-on arm."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

from collect import EXPERIMENT, HERE, read, save, sha
from link import verify
sys.path.insert(0,str(EXPERIMENT/'quantized-continuation-20261123'))
from resume_frozen_suffix import setup, control, FIRST


GUI=r'''
import os
p=Path(ROOT)
assert os.getuid()==1015 and sha(p/'manifest.json')==EXPECTED
attempt,=(p/'batch/runs'/CASE).glob('attempt-*')
ctl,head=journal(attempt/'controller/events.jsonl',live=True)
src,source_head=journal(attempt/'trusted-source/events.jsonl',live=True,source=True)
actions=unique(data(ctl,'native_environment_action'),lambda a:a['step'])
actual=data(src,'native_action_executed')
assert len(actual)>=len(actions)
assert all(n['ok']==r['ok'] for n,r in zip(actions.values(),actual))
assert [a['sequence'] for a in actual]==list(range(1,len(actual)+1))
sub=unique(data(ctl,'actor_submit_timing'),lambda a:a['step'])
done=unique(data(ctl,'observation_finished_timing'),lambda a:a['step'])
asks={}; at=None
for event in ctl:
    if event['kind']=='observation_started_timing':at=event['data']['step']
    if event['kind']=='actual_actor_request':
        assert at not in asks
        asks[at]=event['data']
replies=unique(data(ctl,'actual_actor_reply'),lambda a:a['request_id'])
finished={}
for step, native in actions.items():
    if step not in done:continue
    q=asks[step]; rec=replies[q['request_id']]
    finished[step]={'request_id':q['request_id'],'body_sha256':q['body_sha256'],'reply_sha256':rec['text_sha256'],
                    'submitted_image_sha256':sub[step]['image_sha256'],'actual_native_action':native['payload'],
                    'native_action_ok':native['ok']}
print(json.dumps({'journal_head':head,'trusted_capture_head':source_head,'finished_native_action_decisions':finished}))
'''


MODEL=r'''
import os
p=Path(ROOT)
assert os.getuid()==1033 and sha(p/'manifest.json')==EXPECTED
records=model_extract(p,Path(OUTPUT),read(p/'plan.json'))
bound={x['step']:{'request_id':rid,'body_sha256':x['body_sha256'],'reply_sha256':x['reply_sha256'],
                   'actual_first_forward_image_sha256':x['current_image_sha256'],'actual_first_forward':x['actual_forward'],
                   'natural_EOS':x['natural_EOS'],'forward_calls':x['forward_calls']}
       for rid,x in records['requests'].items()}
assert len(bound)==len(records['requests'])
print(json.dumps({'primary_head':records['primary_chain_head'],'actual_reply_steps':bound}))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger',type=Path)
    parser.add_argument('--run',default=FIRST,help='Frozen recovery-on arm to compare (default: initial white-on).')
    args=parser.parse_args()
    verify(args.ledger)
    setup()
    queue=read(control.PACKAGE/'plan.json')['queue']
    slot,=[r for r in queue if r['run_id']==args.run]
    assert slot['arm']=='on' and slot['condition']!='clean_control'
    ref,=[r['evidence'] for r in read(args.ledger/'private-linked.json')['rows']
          if r['slot']['task_id']==slot['task_id'] and r['slot']['condition']=='clean_control'
          and r['slot']['arm']=='on']
    assert ref['version']=='NF4' and ref['official_score_bound']
    clean={r['step']:r for r in ref['steps']}
    core=(HERE/'extract_on_host.py').read_text(encoding='utf-8')
    load=f'CASE={args.run!r}\n__name__="read_only_library"\n'+core+'\n'
    slots=[r['run_id'] for r in queue]
    settings=f'OWNED_RUNS={slots!r}\nTARGET_RUNS={[args.run]!r}\nOLD_PRIMARY_HEAD=None\nOLD_FLASH_HEAD=None\n'
    with ThreadPoolExecutor(max_workers=2) as executor:
        reads={h:executor.submit(control.remote,h,control.prefix(h)+load+code,
                                 'compare-live-recovery-prefix',timeout=70)
               for h,code in [('3090',settings+MODEL),('4090',GUI)]}
        proofs={h:f.result() for h,f in reads.items()}
    browser=proofs['4090']['result']['finished_native_action_decisions']
    actor=proofs['3090']['result']['actual_reply_steps']
    compared=[]
    for step in sorted(map(int,browser.keys() & actor.keys() & {str(k) for k in clean})):
        gui,m=browser[str(step)],actor[str(step)]
        assert all(m[k]==gui[k] for k in ('request_id','body_sha256','reply_sha256'))
        assert m['actual_first_forward'] and m['natural_EOS'] and m['forward_calls']>0
        assert m['actual_first_forward_image_sha256']==gui['submitted_image_sha256']
        old=clean[step]
        assert old['actual_first_forward'] and old['main']['natural_EOS']
        compared.append({'decision':step,'body_identical':old['main']['body_sha256']==m['body_sha256'],
                         'delivered_current_image_identical':old['main']['current_image_sha256']==m['actual_first_forward_image_sha256'],
                         'reply_identical':old['main']['reply_sha256']==m['reply_sha256'],
                         'native_action_and_result_identical':bool(old['executed'] and
                            old['executed']['payload']==gui['actual_native_action'] and
                            old['executed']['ok']==gui['native_action_ok'])})
    assert [r['decision'] for r in compared]==list(range(1,len(compared)+1))
    matched=0
    for row in compared:
        if not all(v for k,v in row.items() if k!='decision'):break
        matched+=1
    receipts={}
    for h,p in proofs.items():
        d=Path(p['operation']);verify(d)
        receipts[h]={'operation':str(d),'seal_sha256':sha(d/'seal.json')}
    new=HERE/'live-observation-evidence'/str(time.time_ns());new.mkdir(exist_ok=False)
    report={'clean_reference_terminal_sha256':ref['terminal_sha256'],'ledger_seal_sha256':sha(args.ledger/'seal.json'),
            'n_actions_compared':len(compared),'matching_prefix_actions':matched,'per_decision':compared,
            'observed_live_run':args.run,'receipts':receipts,
            'comparison_of_existing_calls_only':True,'official_outcome_not_inferred':True}
    save(new/'clean-reference-comparison.json',report)
    save(new/'seal.json',{'clean-reference-comparison.json':sha(new/'clean-reference-comparison.json')})
    print(json.dumps({'receipt':str(new),'compared':len(compared),'matching_prefix_actions':matched,
                      'first_difference':next((r for r in compared if r['decision']==matched+1),None)}))


if __name__=='__main__':main()
