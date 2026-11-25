"""Evidence-preserving SSH operations for this new linked attempt only."""
from pathlib import Path
import argparse
import importlib.util
import json
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
spec = importlib.util.spec_from_file_location('prior_remote_transport', BASE/'full-gui-single-evidence-20261108-01/remote_control.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
transport.HERE = HERE  # All NEW operation receipts live here; old sources untouched.
remote = transport.remote
sha = transport.sha
save = transport.save
ROOT = '/home/researcher/jev-defense-four-gpu-20261106/repair-evidence-20261109-01'
PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/repair-evidence-20261109-01'
GUI_ROOT = '/data/researcher/jev-defense-four-gpu-20261106/repair-evidence-20261109-01'

def inspect_resources():
    code = '''
from pathlib import Path
import hashlib,json,os,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106')
p=b/'resource-attempt-20261106-01/lease.json'
lease=json.loads(p.read_bytes());h=lease['holder'];proc=Path('/proc',str(h['pid']))
actual={'pid':h['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]}
assert all(str(actual[k])==str(h[k])for k in actual)
locks=[]
for r in lease['lock_records']:
 fd=proc/'fd'/str(r['fd']);info=(proc/'fdinfo'/str(r['fd'])).read_text()
 assert os.readlink(fd)==r['path'] and fd.stat().st_ino==r['inode'] and 'WRITE '+str(h['pid'])in info
 locks.append({'path':r['path'],'inode':fd.stat().st_ino,'device':fd.stat().st_dev,'actual_fdinfo':info})
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
processes=[]
for row in compute.splitlines():
 if not row.strip():continue
 u,pid,m=[s.strip()for s in row.split(',')];p=Path('/proc',pid)
 processes.append({'gpu_uuid':u,'pid':int(pid),'used_mib':m,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()})
old=[]
for path in [b/'full-gui-single-evidence-20261108-01/launcher-process.json',b/'full-gui-single-evidence-20261108-01/worker/process.json']:
 v=json.loads(path.read_bytes());p=Path('/proc',str(v['pid']))
 old.append({'record':str(path),'actual_absent':not p.exists(),'old_identity':v})
print(json.dumps({'time':time.time(),'actual_holder':actual,'held_locks':locks,'gpu':gpu,'actual_compute':processes,'old_exited':old,'lease_sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,'model_calls':0}))
'''
    raw, target = remote('3090', code, 'actual-resources', timeout=55)
    v = json.loads(raw)
    print(json.dumps({'evidence': str(target), 'holder': v['actual_holder'], 'locks': len(v['held_locks']), 'gpu': v['gpu'], 'compute': v['actual_compute'], 'old_all_absent': all(r['actual_absent'] for r in v['old_exited'])}))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['resources']);a=p.parse_args()
    if a.action=='resources':inspect_resources()
