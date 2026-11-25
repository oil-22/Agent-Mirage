"""Read sealed native call accounting without new inference or GPU allocation."""
import json
import time
from control import HERE, OUT, R3090, remote, save, sha
from capture_live_evidence import COMMON

code = 'ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\n' + COMMON + r'''
r=Path(ROOT);p=Path(PACKAGE);calls=[]
for d in sorted((r/'primary/requests').iterdir()):
 if not(d/'seal.json').exists()or not(d/'native-call.json').exists():continue
 s=json.loads((d/'seal.json').read_bytes())
 for name in ['wire-request.bin','actual-generation.json','native-call.json','response.json']:
  assert sha(d/name)==s[name]
 w=json.loads((d/'wire-request.bin').read_bytes());g=json.loads((d/'actual-generation.json').read_bytes());n=json.loads((d/'native-call.json').read_bytes());a=json.loads((d/'response.json').read_bytes())
 assert g['output_ids']==n['generated_ids']and g['natural_EOS']
 assert a['request_sha256']==sha(d/'wire-request.bin')and a['request_id']==w['request_id']
 calls.append({'directory':str(d),'seal_sha256':sha(d/'seal.json'),'run_id':w['run_id'],'decision':w['decision_index'],'input_tokens':g['input_tokens'],'output_tokens':g['output_tokens'],'native_seconds':n['seconds'],'request_seconds_with_audit':a['seconds_with_audit'],'natural_EOS':True,'process_lifetime_memory_snapshot':g['memory']})
flashes=[]
for d in sorted((p/'flash/service/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 s=json.loads((d/'seal.json').read_bytes());assert sha(d/'response.json')==s['response.json']
 a=json.loads((d/'response.json').read_bytes())
 flashes.append({'request_id':a['request_id'],'decision':a['decision'],'seal_sha256':sha(d/'seal.json')})
print(json.dumps({'time':time.time(),'main':calls,'Flash':flashes,'primary_process':json.loads((r/'primary/process.json').read_bytes()),'Flash_process':json.loads((p/'flash/service/process.json').read_bytes()),'actual_primary':identity(json.loads((r/'primary/process.json').read_bytes())['pid']),'actual_Flash':identity(json.loads((p/'flash/service/process.json').read_bytes())['pid']),'memory_peak_scope':'primary support.memory values are process-lifetime high-water marks and can include capacity preflight, not isolated per-call peaks','capacity_generations_excluded':3,'new_model_GUI_calls':0}))
'''
raw, operation = remote('3090', code, 'sealed-GUI-call-usage-snapshot', timeout=55)
value = json.loads(raw)
dest = HERE / ('usage-snapshot-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'source.json', value)
runs = {}
for call in value['main']:
    row = runs.setdefault(call['run_id'], {'calls': 0, 'input_tokens': 0, 'output_tokens': 0,
                                         'summed_native_seconds': 0.0, 'summed_request_seconds_with_audit': 0.0})
    row['calls'] += 1
    row['input_tokens'] += call['input_tokens']
    row['output_tokens'] += call['output_tokens']
    row['summed_native_seconds'] += call['native_seconds']
    row['summed_request_seconds_with_audit'] += call['request_seconds_with_audit']
summary = {'source_operation': str(operation), 'source_sha256': sha(dest / 'source.json'),
           'time': value['time'], 'main_EOS_replies': len(value['main']), 'by_run': runs,
           'Flash_replies': len(value['Flash']),
           'Flash_YES': sum(v['decision'] == 'YES' for v in value['Flash']),
           'Flash_NO': sum(v['decision'] == 'NO' for v in value['Flash']),
           'deployment_reserved_GPUs': {'main': 7, 'Flash': 1},
           'peak_memory_scope': value['memory_peak_scope'],
           'exclusions': 'Capacity generation, all previous engineering attempts/load/hash/audit work and old GUI attempts are not included in GUI native-call sums. Reserved GPU seconds require a separately bounded reservation interval.',
           'not_walltime_currency_energy_or_savings': True, 'new_model_GUI_calls': 0,
           'Mirage_reduction': None}
save(dest / 'summary.json', summary)
save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
print(json.dumps({'usage': str(dest), 'main_EOS': summary['main_EOS_replies'],
                  'Flash_YES': summary['Flash_YES'], 'Flash_NO': summary['Flash_NO'],
                  'summed_GUI_native_seconds': sum(v['summed_native_seconds'] for v in runs.values()),
                  'new_model_GUI_calls': 0}))
