"""Read-only one-shot development inspection; never submits a model request."""
import argparse,json
from pathlib import Path
from remote import remote
p=argparse.ArgumentParser();p.add_argument('receipt');a=p.parse_args()
here=Path(__file__).resolve().parent;launch=json.loads((here/a.receipt).read_text())
code=r'''
import pathlib,json,time,hashlib
root=pathlib.Path(ROOT);log=pathlib.Path(LOG);release=pathlib.Path(RELEASE)
summary=root/'summary.json'
results={p.name:json.loads(p.read_text())for p in root.glob('*-result.json')}
events=[]
for p in root.glob('*/events.jsonl'):
 lines=p.read_text().splitlines()
 for line in lines:
  try:e=json.loads(line)
  except json.JSONDecodeError:continue
  if e['kind']in {'verifier_format_failure','verdict','state_invalidated','history_report_crosscheck'}or(e['kind']=='verifier_raw'and e['data'].get('phase')in {'completion','completion_relation','history_report'}):events.append({'case':p.parent.name,**e})
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
print(json.dumps({'time':time.time(),'running':pathlib.Path('/proc/'+str(PID)).exists(),'summary':json.loads(summary.read_text())if summary.exists()else None,'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest()if summary.exists()else None,'release_bindings':bindings,'results':results,'log_tail':log.read_text()[-1700:]if log.exists()else None,'events':events},ensure_ascii=False))
'''.replace('ROOT',repr(launch['root'])).replace('LOG',repr(launch['log'])).replace('PID',repr(launch['pid'])).replace('RELEASE',repr(launch['release']))
data=json.loads(remote(code,host='4090'))
out=here/(Path(a.receipt).stem.replace('-launch','')+'-progress.json')
out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
short=[]
for row in data['results'].values():
    item={k:row[k]for k in ['case','passed_predeclared_expectation','verifier_calls']if k in row}
    if 'probe'in row:item.update(image_only=row['probe']['image_only_assessment']['status'],agrees=row['probe']['agrees'])
    short.append(item)
last_read=next((e for e in reversed(data['events'])if e['kind']=='verifier_raw'),None)
print(json.dumps({'saved':str(out),'running':data['running'],'passed':data['summary'].get('passed')if data['summary']else None,'cases':short,'log_tail':data['log_tail'],'last_independent_raw':last_read,'errors':[e for e in data['events']if e['kind']=='verifier_format_failure']},ensure_ascii=False))
