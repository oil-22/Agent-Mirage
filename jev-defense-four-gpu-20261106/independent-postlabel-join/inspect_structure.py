import json,hashlib
from pathlib import Path
root=Path(__file__).parent
raw=(root/'sources/final-events.jsonl').read_bytes()
lines=raw.splitlines(keepends=True)
events=[json.loads(x) for x in lines]
e=events[0]; base={k:v for k,v in e.items() if k!='sha256'}
for ascii_ in (False,True):
 for sep in (None,(',',':')):
  h=hashlib.sha256(json.dumps(base,ensure_ascii=ascii_,sort_keys=True,separators=sep).encode()).hexdigest()
  if h==e['sha256']: print('CANONICAL',ascii_,sep)
print('PREFIX',len(b''.join(lines[:734])),hashlib.sha256(b''.join(lines[:734])).hexdigest())
for seq in (17,19,20,21,22,51,541,542,543,734,735,736,737,738,739,740,741,742,743):
 e=events[seq];d=e['data']
 def summarize(x):
  if isinstance(x,dict): return {k:summarize(v) for k,v in x.items()}
  if isinstance(x,list): return [summarize(v) for v in x]
  if isinstance(x,str) and len(x)>1000: return '[large string length='+str(len(x))+',utf8sha256='+hashlib.sha256(x.encode()).hexdigest()+']'
  return x
 print(json.dumps({'seq':seq,'kind':e['kind'],'sha256':e['sha256'],'data':summarize(d)},ensure_ascii=False))
tpath=Path('D:/MultiModel/jev-defense-four-gpu-20261106/gui-runtime-failure-public-1793982609444370800/terminal/technical-failure.json')
t=json.loads(tpath.read_text(encoding='utf-8-sig'))
print('TECH',json.dumps({k:v for k,v in t.items() if k not in ('calls','blocked_reason')},ensure_ascii=False))
print('CALLS',len(t['calls']),[ {k:c.get(k) for k in ('status','kind','role','operation','call_index','decision_index','attempt_index','input_tokens','output_tokens','receipt','request_id')} for c in t['calls'][-2:]])
