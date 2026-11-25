"""Compare the two already sealed actual masked-image Flash calls; no inference."""
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha

CODE = r'''
import hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for case in CASES:
 p=Path(case['request']['root']);seal=json.loads((p/'seal.json').read_bytes())
 assert sha(p/'seal.json')==case['request']['seal_sha256']
 data={}
 for name in ['forward-trace.json','native-request.json','raw-readout.json','response.json']:
  assert sha(p/name)==seal[name];data[name]=json.loads((p/name).read_bytes())
 assert len(data['forward-trace.json'])==1
 trace=data['forward-trace.json'][0]
 assert trace['past_key_values']is None and trace['use_cache']is False
 assert data['response.json']['request_id']==case['request']['request_id']
 rows.append({'run_id':case['run_id'],'request_id':case['request']['request_id'],
              'image_sha256':case['request']['image_sha256'],
              'probabilities':case['request']['probabilities'],'decision':case['request']['decision'],
              'request_seal_sha256':sha(p/'seal.json'),'data':data})
a,b=rows
print(json.dumps({'rows':[{k:v for k,v in r.items()if k!='data'}for r in rows],
 'same_mask_PNG':a['image_sha256']==b['image_sha256'],
 'all_actual_forward_inputs_exactly_equal':a['data']['forward-trace.json']==b['data']['forward-trace.json'],
 'native_requests_exactly_equal':a['data']['native-request.json']==b['data']['native-request.json'],
 'raw_readouts_exactly_equal':a['data']['raw-readout.json']==b['data']['raw-readout.json'],
 'both_calls_no_past_KV_and_use_cache_false':True,'new_model_GUI_calls':0}))
'''


def main():
    assert not (HERE/'buttons-information-audit-current.json').exists()
    cases=[];bindings=[]
    for root in sorted(HERE.glob('trajectory-audit-button16-*-buttons_only-gate-*')):
        if not(root/'seal.json').exists():continue
        for n,h in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/n)==h
        summary=json.loads((root/'summary.json').read_bytes());route=summary['route']
        assert route['injection_triggered']
        rid=route['attack_Flash'][0]['data']['request_id']
        request=next(r for r in json.loads((root/'request-results.json').read_bytes())['Flash']if r['request_id']==rid)
        assert request['image_sha256']==route['attack']['delivered_sha256']
        cases.append({'run_id':route['run_id'],'request':request})
        bindings.append({'root':str(root),'seal_sha256':sha(root/'seal.json')})
    assert {r['run_id']for r in cases}=={'button16-T114-buttons_only-gate','button16-T125-buttons_only-gate'}
    root=HERE/('buttons-information-audit-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'source-bindings.json',{'trajectory_audits':bindings,'cases':cases})
    raw,op=remote('3090','CASES='+repr(cases)+'\n'+CODE,'read-only-two-original-buttons-mask-inputs')
    result={'operation':str(op),**json.loads(raw)};save(root/'result.json',result)
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    save(HERE/'buttons-information-audit-current.json',{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'root':str(root),**result}))


if __name__=='__main__':main()
