"""Independently rehash the recorded first-forward tensor bytes of sealed NF4 slots."""

import argparse
import json
from pathlib import Path
import time

from collect import HERE, control, manifest_for, measurement_version, read, save, sha, stages
from link import verify


AUDIT=r'''
import os,shutil,subprocess
p=Path(ROOT);output=Path(OUTPUT);primary=output/'primary'
assert os.getuid()==1033 and sha(p/'manifest.json')==EXPECTED
os.nice(15)
ionice=shutil.which('ionice')
if ionice:
    io_idle=subprocess.run([ionice,'-c','3','-p',str(os.getpid())],capture_output=True).returncode==0
else:
    io_idle=False
events,head=journal(primary/'journal/events.jsonl',live=True)
request_events=unique(data(events,'actor_request'),lambda a:a['request_id'])
reply_events=unique(data(events,'actor_reply_sealed'),lambda a:a['request_id'])
end_events=unique(data(events,'run_end'),lambda a:a['run_id'])
rows=[]
for prior in REQUESTS:
    rid=prior['request_id']; run=prior['run']; n=prior['step']
    assert end_events[run]['terminal_sha256']==prior['terminal_sha256']
    event=request_events[rid]; q=Path(event['folder']); seal_path=q/'seal.json'
    assert q.is_relative_to(primary/'requests') and str(q)==prior['request_directory']
    assert prior['seal_sha256']==sha(seal_path)
    assert event['wire_sha256']==prior['wire_sha256'] and event['decision']==n and event['run_id']==run
    if prior['natural_EOS']:
        assert reply_events[rid]['seal_sha256']==prior['seal_sha256']
    seal=read(seal_path); first=read(sealed(q,seal,'first-forward.json')); prepared=read(sealed(q,seal,'prepared.json'))
    assert first.keys()==prepared.keys() and 'input_ids' in first
    tensors={}
    for key,meta in first.items():
        assert all(meta[k]==prepared[key][k] for k in ('shape','dtype','bytes','sha256'))
        checked_tensor(q,seal,meta,full_hash=True)
        tensors[key]={k:meta[k] for k in ('shape','dtype','bytes','sha256')}
    rows.append({'run':run,'step':n,'request_id':rid,'request_seal_sha256':prior['seal_sha256'],
                 'forward_manifest_sha256':seal['first-forward.json'],'first_forward_tensors':tensors})
print(json.dumps({'requests':rows,'journal_head':head,'idle_priority_io':io_idle,
    'actual_gpu_model_browser_or_score_calls':0,'tensor_bytes_rehashed':sum(
        t['bytes'] for r in rows for t in r['first_forward_tensors'].values())}))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger',type=Path)
    parser.add_argument('stage',choices=[k for k in stages() if measurement_version(k)=='NF4'])
    args=parser.parse_args()
    verify(args.ledger)
    ledger=read(args.ledger/'private-linked.json')
    requests=[]
    for arm in ledger['rows']:
        if arm['stage_id']!=args.stage or arm['status']!='verified_terminal':continue
        tape=arm['evidence']
        assert tape['version']=='NF4' and tape['model_run_end_bound']
        for step in tape['steps']:
            if not step['actual_first_forward']:continue
            record=step['main']
            requests.append({'run':arm['slot']['run_id'],'step':step['step'],'request_id':step['request']['request_id'],
                'terminal_sha256':tape['terminal_sha256'],'natural_EOS':record['natural_EOS'],
                'wire_sha256':record['wire_sha256'],'seal_sha256':record['seal_sha256'],
                'request_directory':record['runtime_request_directory']})
    assert requests and len({r['request_id'] for r in requests})==len(requests)
    ptr, mf, _=manifest_for(args.stage)
    assert {r['run'] for r in requests} <= {r['run_id'] for r in read(Path(ptr['runtime'])/'plan.json')['queue']}
    dst=HERE/'forward-byte-audits'/str(time.time_ns());dst.mkdir(parents=True,exist_ok=False)
    control.ROOT=dst
    src=(HERE/'extract_on_host.py').read_text(encoding='utf-8')
    pre=(f"ROOT={mf['package3090']!r}\nOUTPUT={mf['output3090']!r}\nEXPECTED={ptr['manifest_sha256']!r}\n"
         f"REQUESTS={requests!r}\n__name__='evidence_library'\n")
    receipt=control.remote('3090',pre+src+'\n'+AUDIT,'check-sealed-NF4-forward-raw-bytes',timeout=180)
    op=Path(receipt['operation']);verify(op)
    result=receipt['result']; proof=result['requests']
    assert [r['request_id'] for r in proof]==[r['request_id'] for r in requests]
    summary={'stage':args.stage,'ledger_sha256':sha(args.ledger/'seal.json'),'operation_seal_sha256':sha(op/'seal.json'),
             'operation':str(op),'terminals':len({r['run'] for r in requests}),
             'request_count':len(requests),'tensor_bytes_rehashed':result['tensor_bytes_rehashed'],
             'tensor_count':sum(len(r['first_forward_tensors']) for r in proof),
             'read_existing_recorded_bytes_only':True,'this_audit_did_not_run_new_forwards':True}
    save(dst/'summary.json',summary)
    save(dst/'seal.json',{'summary.json':sha(dst/'summary.json')})
    print(json.dumps({'audit':str(dst),**summary}))


if __name__=='__main__':main()
