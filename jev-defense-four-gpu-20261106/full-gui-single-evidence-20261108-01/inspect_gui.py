"""Read actual GUI process and hash-chained live journals; no HTTP/model/actions."""
import json
from remote_control import ROOT4090,remote

CODE='ROOT='+repr(ROOT4090)+'\n'+r'''
from pathlib import Path
import collections,hashlib,json,os,time
r=Path(ROOT);out={'time_unix':time.time(),'new_model_HTTP_GUI_calls':0,'remote_read_only':True}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
for name in ['background/launch.json','control/process.json','control/runner-process.json','control/exit.json','batch/status.json']:
 p=r/name
 if p.exists():
  value=json.loads(p.read_bytes())
  if name.endswith('process.json'):value={'record':value,'actual':identity(value['pid'])}
  elif name=='background/launch.json':value={'record':value,'actual':identity(value['identity']['pid'])}
  out[name]={'value':value,'sha256':sha(p)}
for p in [r/'background/outer.log',r/'control/runner.log']:
 if p.exists():out[str(p.relative_to(r))]={'bytes':p.stat().st_size,'tail':p.read_bytes()[-3200:].decode(errors='replace')}
out['runs']=[]
for run in sorted((r/'batch/runs').glob('*')):
 for a in sorted(run.glob('attempt-*')):
  d={'run_id':run.name,'attempt':str(a)}
  for name in ['complete.json','technical-failure.json','failure.json']:
   p=a/name
   if p.exists():
    v=json.loads(p.read_bytes());v.pop('calls',None);d[name]={'sha256':sha(p),'value':v}
  p=a/'events.jsonl'
  if p.exists():
   previous='0'*64;events=[];counts=collections.Counter();incomplete=False
   for line in p.read_bytes().splitlines():
    try:v=json.loads(line)
    except ValueError:incomplete=True;break
    sig=v.pop('sha256');assert v['seq']==len(events) and v['previous']==previous and hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
    previous=sig;events.append(v);counts[v['kind']]+=1
   d['journal']={'events':len(events),'head':previous,'kind_counts':dict(counts),'last_kind':events[-1]['kind'] if events else None,'incomplete_last_line':incomplete}
   d['latest_decisions']=[{'kind':e['kind'],'data':e['data']} for e in events if e['kind'] in ['executed','decision_accepted','decision_blocked']][-1:]
   # Candidate texts stay in the immutable original journal; snapshots report counts, not semantic labels.
   d.pop('latest_decisions',None)
  d['captured_screenshots']=len(list((a/'screenshots').glob('*-captured.png')))
  out['runs'].append(d)
print(json.dumps(out,ensure_ascii=False))
'''
if __name__=='__main__':
    out,target=remote('4090',CODE,'inspect-full-GUI',timeout=55)
    v=json.loads(out)
    print(json.dumps({'evidence':str(target),'time_unix':v['time_unix'],
        'state':v.get('batch/status.json',{}).get('value'),
        'actual_runner':v.get('control/runner-process.json',{}).get('value',{}).get('actual'),
        'exit':v.get('control/exit.json',{}).get('value'),'runs':v['runs'],
        'log_tail':v.get('control/runner.log',{}).get('tail') if v.get('control/exit.json') else None},ensure_ascii=False))
