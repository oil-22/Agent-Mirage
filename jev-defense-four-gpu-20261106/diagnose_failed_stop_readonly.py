"""Root read-only stop diagnosis; no signals, HTTP, or remote writes."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

BASE = Path(__file__).resolve().parent
REMOTE = r'''
import hashlib, json, os, subprocess, time
from pathlib import Path
group = Path('/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243')
lease = json.loads(Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json').read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def identity(pid):
    root = Path('/proc')/str(pid)
    if not root.exists(): return None
    fields = (root/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':int(pid),'uid':root.stat().st_uid,'state':fields[0],
        'start_ticks':fields[19], 'command':(root/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()}
expected = {'holder':lease['holder'],'launcher':json.loads((group/'process.json').read_bytes())}
for role in ('primary','pplx_flash'):
    expected[role] = json.loads((group/'processes'/(role+'.json')).read_bytes())['identity']
processes={}
for role, old in expected.items():
    actual=identity(old['pid'])
    row={'expected':old,'actual':actual,'identity_matches':actual is not None and all(str(actual[k])==str(old[k]) for k in ('pid','uid','command','start_ticks'))}
    if row['identity_matches']:
        row['locks']=[]
        for lock in lease['lock_records']:
            fd=Path('/proc',str(old['pid']),'fd',str(lock['fd']))
            info=Path('/proc',str(old['pid']),'fdinfo',str(lock['fd']))
            row['locks'].append({'path':lock['path'],'held':fd.exists() and os.readlink(str(fd))==lock['path'] and fd.stat().st_ino==lock['inode'] and 'lock:' in info.read_text()})
    processes[role]=row
files={}
for name in ('launcher-failure.json','stop-requested.json','exit.json','terminal-sha256.json','primary/stopped.json','pplx_flash/stopped.json'):
    path=group/name
    files[name]={'exists':path.exists()}
    if path.exists():
        files[name].update(sha256=sha(path),bytes=path.stat().st_size)
        if name!='terminal-sha256.json': files[name]['value']=json.loads(path.read_bytes())
logs={}
for name in ('primary.log','pplx_flash.log'):
    path=group/name
    logs[name]={'sha256':sha(path),'bytes':path.stat().st_size,'tail':path.read_text(errors='replace')[-6000:]}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,memory.used','--format=csv,noheader,nounits'],universal_newlines=True)
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],universal_newlines=True)
print(json.dumps({'time':time.time(),'group':str(group),'processes':processes,'files':files,'logs':logs,'gpu_csv':gpu,'compute_csv':compute,'HTTP_model_GUI_scorer_signals_remote_writes':0}))
'''

if __name__ == '__main__':
    value = json.loads(remote(REMOTE, timeout=90))
    output = BASE / 'root-stop-diagnosis' / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode('utf8')
    (output / 'receipt.json').write_bytes(raw)
    (output / 'seal.json').write_text(json.dumps({'receipt.json':hashlib.sha256(raw).hexdigest()}),encoding='utf8')
    print(json.dumps({'receipt':str(output/'receipt.json'),'sha256':hashlib.sha256(raw).hexdigest(),
        'processes':{role:{key:row.get(key) for key in ('actual','identity_matches','locks')} for role,row in value['processes'].items()},
        'files':value['files'],'logs':value['logs'],'gpu_csv':value['gpu_csv'],'compute_csv':value['compute_csv']}))
