from pathlib import Path
import hashlib, json, os, subprocess, time
B=Path('/home/researcher/jev-defense-four-gpu-20261106')
L=B/'resource-attempt-20261106-01/lease.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
lease=json.loads(L.read_bytes());h=lease['holder'];actual=identity(h['pid'])
assert all(actual[k]==h[k] for k in ['pid','uid','command','start_ticks'])
assert actual['state'] not in ['Z','X']
locks=[]
for r in lease['lock_records']:
 p=Path('/proc',str(h['pid']));fd=p/'fd'/str(r['fd']);info=(p/'fdinfo'/str(r['fd'])).read_text()
 assert os.readlink(fd)==r['path'] and fd.stat().st_ino==r['inode'] and 'WRITE '+str(h['pid']) in info
 locks.append(r['path'])
out={'time':time.time(),'uid':os.getuid(),'holder':actual,'lease_sha256':sha(L),'verified_locks':locks,'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True),'compute':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True),'model_calls_by_inspector':0}
for n in ['flash-preparation/remote-evidence/identity-binding/receipt.json','flash-preparation/download-attempts/1793972286914423476/download-complete-receipt.json']:
 p=B/n
 out[n]={'exists':p.exists(),'sha256':sha(p) if p.exists() else None}
for name in ['jev_style','neohorse']:
 p=Path('/home/researcher/jev-defense-local-20261102/models-verified')/name/'download-complete-receipt.json'
 v=json.loads(p.read_bytes());out[name]={'receipt_sha256':sha(p),'keys':list(v),'first_file':v.get('files',[None])[0]}
root=B/'binary-gate-comparison-20261112'
out['comparison_exists']=root.exists()
if root.exists():
 for n in ['launch.json','terminal.json']:
  p=root/n
  if p.exists():out[n]=json.loads(p.read_bytes())
print(json.dumps(out,ensure_ascii=False))
