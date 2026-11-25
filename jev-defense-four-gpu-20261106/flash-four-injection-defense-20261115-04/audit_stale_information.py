"""Compare existing real Flash inputs for normal PNG versus its later replay.

Reads already sealed completed stale trajectories only. No inference, GUI action,
relabeling, prompt change, injection hints or new evaluation trials.
"""
import json
import sys
import time
from pathlib import Path

from control import HERE, remote, save, sha


REMOTE = r'''
import hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=[]
for case in CASES:
 entries=[]
 for label in ['original','replay']:
  saved=case[label];p=Path(saved['root']);seal=json.loads((p/'seal.json').read_bytes())
  assert sha(p/'seal.json')==saved['seal_sha256']
  for name in ['forward-trace.json','native-request.json','raw-readout.json','response.json']:
   assert sha(p/name)==seal[name]
  trace=json.loads((p/'forward-trace.json').read_bytes());assert len(trace)==1
  trace=trace[0];assert trace['past_key_values']is None and trace['use_cache']is False
  request=json.loads((p/'native-request.json').read_bytes())
  response=json.loads((p/'response.json').read_bytes())
  assert response['request_id']==saved['request_id']
  entries.append({'label':label,'request_id':response['request_id'],'root':str(p),
                  'seal_sha256':sha(p/'seal.json'),'trace':trace,'request':request,
                  'readout':json.loads((p/'raw-readout.json').read_bytes()),
                  'probabilities':saved['probabilities'],'decision':saved['decision']})
 a,b=entries
 tensors=[k for k,v in a['trace'].items()if isinstance(v,dict)and'sha256'in v]
 assert {'input_ids','pixel_values','image_grid_thw'}<=set(tensors)
 out.append({'run_id':case['run_id'],'normal_request_id':a['request_id'],
             'replayed_request_id':b['request_id'],'PNG_sha256':case['PNG_sha256'],
             'normal_and_replayed_native_request_exactly_equal':a['request']==b['request'],
             'all_actual_forward_inputs_exactly_equal':a['trace']==b['trace'],
             'tensor_checks':{k:{'shape':a['trace'][k]['shape'],'dtype':a['trace'][k]['dtype'],
                                  'original_sha256':a['trace'][k]['sha256'],
                                  'replayed_sha256':b['trace'][k]['sha256'],
                                  'equal':a['trace'][k]==b['trace'][k]}for k in tensors},
             'both_calls_no_past_KV_and_use_cache_false':True,
             'original_decision':a['decision'],'replayed_decision':b['decision'],
             'original_probabilities':a['probabilities'],'replayed_probabilities':b['probabilities'],
             'raw_readouts_exactly_equal':a['readout']==b['readout'],
             'seals':[a['seal_sha256'],b['seal_sha256']]})
print(json.dumps({'comparisons':out,'new_model_GUI_calls':0}))
'''


def main():
    cases, sources = [], []
    requested = set(sys.argv[1:])
    for audit in sorted(HERE.glob('trajectory-audit-*-stale_replace-gate-*')):
        if not (audit / 'seal.json').exists():
            continue
        for name, expected in json.loads((audit / 'seal.json').read_bytes()).items():
            assert sha(audit / name) == expected
        summary = json.loads((audit / 'summary.json').read_bytes())
        route = summary['route']
        if requested and route['run_id'] not in requested:
            continue
        if not route['injection_triggered']:
            continue
        events = json.loads((audit / 'Controller.json').read_bytes())['result']['events']
        attack = next(v for v in events if v['kind'] == 'PRIVATE_capture_injection' and v['data']['injected'])
        digest = attack['data']['delivered_sha256']
        old = [v for v in events if v['kind'] == 'gate_decision' and v['seq'] < attack['seq']
               and v['data']['decision'] == 'YES' and v['data']['image_sha256'] == digest]
        assert old, 'The replay must bind to an actual earlier accepted image'
        replay = route['attack_Flash'][0]['data']
        results = json.loads((audit / 'request-results.json').read_bytes())['Flash']
        byid = {v['request_id']: v for v in results}
        original = byid[old[-1]['data']['request_id']]
        repeated = byid[replay['request_id']]
        assert original['image_sha256'] == repeated['image_sha256'] == digest
        assert original['revision'] == repeated['revision'] and original['contract_sha256'] == repeated['contract_sha256']
        cases.append({'run_id': route['run_id'], 'PNG_sha256': digest,
                      'original': original, 'replay': repeated})
        sources.append({'root': str(audit), 'seal_sha256': sha(audit / 'seal.json')})
    assert cases, 'Wait for a new completed sealed stale trajectory; never rerun models'
    if requested:
        assert {v['run_id'] for v in cases} == requested
    root = HERE / ('stale-information-audit-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'source-bindings.json', {'sources': sources, 'cases': cases})
    raw, operation = remote('3090', 'CASES=' + repr(cases) + '\n' + REMOTE,
                            'read-only-normal-versus-replayed-actual-inputs')
    result = json.loads(raw)
    save(root / 'result.json', {'operation': str(operation), **result,
                               'normal_PNG_usability_is_not_capture_freshness': True,
                               'no_new_method_deployed': True})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), **result}))


if __name__ == '__main__':
    main()
