"""Read only the terminal and relevant failed-verifier evidence; no HTTP."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE=Path(__file__).resolve().parent
CODE=r'''
import hashlib,json
from pathlib import Path
root=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01')
a=root/'runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
terminal=a/'technical-failure.json'
assert sha(terminal)=='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
events=[]
with(a/'events.jsonl').open()as f:
 for line in f:events.append(json.loads(line))
selected=[]
indices=[i for i,x in enumerate(events)if x['kind']=='verifier_format_failure']
for i in indices:
 start=max(j for j in range(i)if events[j]['kind']=='verifier_request')
 snippet=[{'seq':x['seq'],'kind':x['kind'],'data':x['data']}for x in events[start:i+1]if x['kind']in('verifier_raw','verifier_format_failure')]
 selected.append({'failure_seq':events[i]['seq'],'request_seq':events[start]['seq'],
 'request_data_keys':list(events[start]['data']),
 'request_stage':{k:v for k,v in events[start]['data'].items()if k in('stage','purpose','kind','operation','attempt','format_attempt','retry','decision_index')},'events':snippet})
last=next(x for x in reversed(events)if x['kind']=='candidate')
result={'terminal':json.loads(terminal.read_bytes()),'terminal_sha256':sha(terminal),
 'events_count':len(events),'head':events[-1]['sha256'],'events_sha256':sha(a/'events.jsonl'),
 'format_failures':selected,'last_candidate':{'seq':last['seq'],'data':last['data']},
 'directory_files':[p.name for p in a.iterdir()if p.is_file()],
 'HTTP_model_GUI_calls':0}
print(json.dumps(result,ensure_ascii=False))
'''
if __name__=='__main__':
 out=BASE/'terminal-diagnosis-readonly'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
 try:
  value=remote(CODE,timeout=120,host='4090')
  (out/'actual-diagnostic.json').write_text(value,encoding='utf8')
  (out/'source.py').write_bytes(Path(__file__).read_bytes())
  data=json.loads(value)
  print(json.dumps({'output':str(out),'data':data},ensure_ascii=False))
 finally:
  (out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
