"""Evidence-preserving orchestration for a NEW finite full GUI pilot."""
import argparse, base64, hashlib, io, json, os, subprocess, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PYTHON = 'D:/MultiModel/MultiModelenv/Scripts/python.exe'
SSH = ['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']
ROOT3090 = '/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03'
ROOT4090 = '/data/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf8') as f: json.dump(v,f,ensure_ascii=False,indent=2); f.write('\n')

def remote(host, code, label, timeout=60, interpreter=None, private_prefix=None):
    target=HERE/'operations'/(str(time.time_ns())+'-'+label); target.mkdir(parents=True,exist_ok=False)
    (target/'source.py').write_text(code,encoding='utf8')
    if interpreter is None: interpreter='/opt/whz/conda-envs/webmall-vlm/bin/python' if host=='3090' else '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
    cmd=SSH+[host,interpreter+' -B -']
    try:
        result=subprocess.run(cmd,input=(private_prefix or '')+code,text=True,encoding='utf8',capture_output=True,timeout=timeout)
        (target/'stdout.txt').write_text(result.stdout,encoding='utf8'); (target/'stderr.txt').write_text(result.stderr,encoding='utf8')
        save(target/'receipt.json',{'host':host,'returncode':result.returncode,'public_source_body_sha256':sha(target/'source.py'),
            'private_stdin_prefix_excluded':private_prefix is not None,
            'private_prefix_sha256':None if private_prefix is None else hashlib.sha256(private_prefix.encode()).hexdigest(),'time':time.time()})
    except Exception as e:
        save(target/'failure.json',{'type':type(e).__name__,'message':str(e)});raise
    if result.returncode: raise RuntimeError(str(target)+'\n'+result.stdout[-3000:]+'\n'+result.stderr[-3000:])
    return result.stdout, target

def inspect():
    code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106');r=b/'full-gui-bounded-evidence-20261109-03'
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());h=lease['holder'];actual=identity(h['pid'])
assert all(str(h[k])==str(actual[k]) for k in ['pid','uid','command','start_ticks'])
locks=[]
for row in lease['lock_records']:
 p=Path('/proc',str(h['pid']));fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path'] and fd.stat().st_ino==row['inode'] and 'WRITE '+str(h['pid']) in info
 locks.append(row['path'])
out={'time':time.time(),'holder':actual,'held_locks':locks,'new_model_calls':0,'remote_read_only':True}
for n in ['launcher-process.json','worker/process.json','worker/loaded.json','worker/ready.json','worker/status.json','worker/terminal.json','exit.json']:
 p=r/n
 if p.is_file():
  v=json.loads(p.read_bytes())
  if n.endswith('process.json'):v={'record':v,'actual':identity(v['pid'])}
  if n=='worker/loaded.json':v={k:x for k,x in v.items() if k not in ['actual_cuda_tensors']}
  out[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'value':v}
for p in [r/'worker.log',b/'resource-attempt-20261106-01/full-gui-bounded-evidence-20261109-03.log']:
 if p.is_file():out[str(p)]={'bytes':p.stat().st_size,'tail':p.read_bytes()[-2400:].decode(errors='replace')}
ev=r/'worker/journal/events.jsonl'
if ev.exists():
 previous='0'*64;counts={};n=0
 for raw in ev.read_bytes().splitlines():
  v=json.loads(raw);s=v.pop('sha256');assert v['seq']==n and v['previous']==previous and hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==s
  previous=s;n+=1;counts[v['kind']]=counts.get(v['kind'],0)+1
 out['journal']={'events':n,'head':previous,'kinds':counts,'last_kind':v['kind'],'last_data':v['data']}
out['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
for p in sorted((r/'worker/requests').glob('*/failure.json')):
 out[str(p.relative_to(r))]=json.loads(p.read_bytes())
print(json.dumps(out,ensure_ascii=False))
'''
    out,target=remote('3090',code,'inspect-service',timeout=55)
    v=json.loads(out)
    print(json.dumps({'evidence':str(target),'time':v['time'],
        'holder_nine_locks_verified':len(v['held_locks'])==9,
        'service_status':v.get('worker/status.json',{}).get('value'),
        'ready':v.get('worker/ready.json',{}).get('value'),
        'terminal':v.get('worker/terminal.json',{}).get('value'),
        'exit':v.get('exit.json',{}).get('value'),
        'actual_worker':v.get('worker/process.json',{}).get('value',{}).get('actual'),
        'journal':{k:x for k,x in v.get('journal',{}).items() if k!='last_data'},
        'failures':{k:x for k,x in v.items() if k.endswith('/failure.json')},
        'gpu':v['gpu'],'compute':v['compute']},ensure_ascii=False))

def discover():
    code=r'''
from pathlib import Path
import json,os,subprocess
b=Path('/data/researcher/jev-defense-four-gpu-20261106')
out={'uid':os.getuid(),'root':str(b),'environments':[], 'old_processes':[]}
for p in [b/'gui-migration-three-linked02/gui_once.py', b/'gui-migration-three-linked02/native_environment.py']:
 if p.exists():out[str(p)]=p.read_text()
for p in Path('/data/researcher/venvs').glob('*/bin/python'):
 if any(x in str(p) for x in ['vwa','qwen35','jev']):out['environments'].append(str(p))
for p in Path('/proc').glob('[0-9]*'):
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode()
  if any(x in cmd for x in ['run_image_observer_vwa_validation.py','run_single_evidence_gui.py','gui_once.py','online-three']):out['old_processes'].append({'pid':int(p.name),'command':cmd})
 except (OSError,UnicodeError):pass
print(json.dumps(out,ensure_ascii=False))
'''
    out,target=remote('4090',code,'discover-environment',timeout=55)
    value=json.loads(out);print(json.dumps({'evidence':str(target),'uid':value['uid'],'environments':value['environments'],'old_processes':value['old_processes'],'source_keys':[k for k in value if k.endswith('.py')]}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','discover']);a=p.parse_args()
    {'inspect':inspect,'discover':discover}[a.action]()
