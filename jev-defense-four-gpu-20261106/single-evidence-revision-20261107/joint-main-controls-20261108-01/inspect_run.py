"""Read actual process, FDs, GPU membership, files and journal; no model/HTTP."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
CODE = r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106')
r=b/'single-evidence-revision-20261107/joint-main-controls-20261108-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out={'time_unix':time.time(),'root':str(r),'remote_read_only':True,'new_model_HTTP_GUI_calls':0}
def identity(pid):
 p=Path('/proc')/str(pid)
 if not p.exists():return {'pid':pid,'proc_absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 d={'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),
    'start_ticks':tail[19],'state':tail[0],'locks':[]}
 lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes())
 for row in lease['lock_records']:
  try:
   fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
   d['locks'].append({'path':row['path'],'matches':os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'FLOCK'in info and 'WRITE 2568295'in info})
  except OSError:d['locks'].append({'path':row['path'],'matches':False})
 return d
out['holder']=identity(2568295)
for n in ['launcher-process.json','worker-launch.json','exit.json','worker/process.json','worker/loaded.json',
          'worker/summary.json','worker/terminal.json','worker/failure.json','launcher-failure.json','terminal-manifest.json']:
 p=r/n
 if p.is_file():
  raw=p.read_bytes();v=json.loads(raw)
  if n in ['launcher-process.json','worker/process.json']:v={'record':v,'actual':identity(v['pid'])}
  elif n=='worker-launch.json':v={'record':v,'actual':identity(v['identity']['pid'])}
  elif n=='worker/loaded.json':v={k:x for k,x in v.items()if k not in ['actual_cuda_tensors']}
  elif n=='terminal-manifest.json':
   errors=[k for k,h in v.items()if not(r/k).is_file()or sha(r/k)!=h]
   v={'files':len(v),'all_SHA_verified':not errors,'errors':errors}
  out[n]={'sha256':hashlib.sha256(raw).hexdigest(),'value':v}
for p in sorted((r/'worker/auxiliary').glob('*/result.json')):
 out[str(p.relative_to(r))]={'sha256':sha(p),'value':json.loads(p.read_bytes())}
for p in sorted((r/'worker').glob('C*-result.json')):
 out[str(p.relative_to(r))]={'sha256':sha(p),'value':json.loads(p.read_bytes())}
for p in sorted((r/'worker/judges').glob('*/actual-generation.json')):
 v=json.loads(p.read_bytes());v.pop('output_ids',None)
 out[str(p.relative_to(r))]={'sha256':sha(p),'value':v}
for p in [r/'worker.log',b/'resource-attempt-20261106-01/joint-main-controls-20261108-01.log']:
 if p.is_file():out[str(p)]={'bytes':p.stat().st_size,'last_text':p.read_bytes()[-4200:].decode(errors='replace')}
e=r/'worker/journal/events.jsonl'
if e.exists():
 raw=e.read_bytes();lines=raw.splitlines();previous='0'*64;errors=[];events=[]
 for i,line in enumerate(lines):
  try:v=json.loads(line)
  except ValueError:
   out['journal_tail_pending']=True;break
  saved=v.pop('sha256');canonical=json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
  if v['previous']!=previous or hashlib.sha256(canonical).hexdigest()!=saved or v['seq']!=i:errors.append(i)
  previous=saved;events.append(v)
 out['journal']={'verified_events':len(events),'head':previous,'errors':errors,'prefix_raw_sha256':hashlib.sha256(raw).hexdigest(),
  'kind_counts':{k:sum(v['kind']==k for v in events)for k in set(v['kind']for v in events)},
  'last':{'kind':events[-1]['kind'],'data':events[-1]['data']}if events else None}
out['inflight_request_progress']=[]
for folder in sorted((r/'worker/judges').glob('*')):
 if not folder.is_dir() or (folder/'seal.json').exists():continue
 row={'call':folder.name,'full_request_present':(folder/'request.json').exists(),
      'actual_first_forward_record_present':(folder/'first-forward.json').exists()}
 prepared=folder/'prepared.json'
 if prepared.exists():row['native_input_tokens']=json.loads(prepared.read_bytes())['input_ids']['shape'][-1]
 progress=folder/'generated-token-progress.jsonl'
 if progress.exists():
  raw=progress.read_bytes();lines=raw.splitlines()
  row['progress_records']=len(lines);row['last_progress_record']=lines[-1].decode() if lines else None
 out['inflight_request_progress'].append(row)
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits'],text=True)
print(json.dumps(out,ensure_ascii=False))
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', choices=['01', '02', '03'], default='01')
    options = parser.parse_args()
    CODE = CODE.replace('joint-main-controls-20261108-01', 'joint-main-controls-20261108-' + options.attempt)
    target = HERE / 'progress-evidence' / str(time.time_ns()); target.mkdir(parents=True, exist_ok=False)
    (target / 'source.py').write_text(CODE, encoding='utf8')
    r = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15', '3090', '/opt/whz/conda-envs/webmall-vlm/bin/python', '-'],
        input=CODE.encode(), capture_output=True, timeout=60)
    (target / 'stdout.json').write_bytes(r.stdout); (target / 'stderr.txt').write_bytes(r.stderr)
    if r.returncode:
        print(r.stderr.decode()); raise SystemExit(r.returncode)
    d = json.loads(r.stdout)
    def console_projection(value):
        if isinstance(value, list):
            return [console_projection(v) for v in value]
        if isinstance(value, dict):
            return {k: console_projection(v) for k, v in value.items() if k != 'resource_evidence'}
        return value
    compact = {'time_unix': d['time_unix'], 'evidence_directory': str(target),
               'GPU': d['GPU'], 'compute': d['compute'], 'inflight_request_progress':d.get('inflight_request_progress',[])}
    for key in ['launcher-process.json', 'worker/process.json']:
        if key in d:
            actual = d[key]['value']['actual']
            compact[key] = {k: v for k, v in actual.items() if k != 'locks'}
            compact[key]['all_nine_locks_match'] = len(actual.get('locks', [])) == 9 and all(x['matches'] for x in actual.get('locks', []))
    for key in ['exit.json', 'worker/loaded.json', 'worker/summary.json', 'worker/terminal.json', 'worker/failure.json',
                'launcher-failure.json', 'terminal-manifest.json']:
        if key in d:
            compact[key] = console_projection(d[key])
    if 'journal' in d:
        compact['journal'] = {k: v for k, v in d['journal'].items() if k != 'last'}
        compact['journal']['last_kind'] = None if not d['journal']['last'] else d['journal']['last']['kind']
    for key, value in d.items():
        if key.endswith('/result.json') or '-result.json' in key or key.endswith('/actual-generation.json'):
            compact[key] = value
        elif key.endswith('.log'):
            compact[key] = {'bytes': value['bytes'], 'last_text': value['last_text'][-2000:]}
    print(json.dumps(compact, ensure_ascii=False))
    (target / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in target.iterdir() if p.is_file()}, indent=2), encoding='utf8')
