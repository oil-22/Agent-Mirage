"""Read-only actual UID/command/start/held inherited locks/compute/request proof."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import hashlib,json,os,subprocess,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def actual(saved):
 p=Path('/proc',str(saved['pid']));assert p.exists()
 s=(p/'stat').read_text().rsplit(')',1)[1].split();v={'pid':saved['pid'],'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 assert v['state']not in ['Z','X']and all(v[k]==saved[k]for k in ['pid','uid','command','start_ticks'])
 return v
p=Path(P);o=Path(O);lease=json.loads((o/'lease.json').read_bytes());assert lease['manifest_sha256']==MANIFEST
records={'launcher':lease['holder'],'primary':json.loads((o/'primary/process.json').read_bytes()),'Flash':json.loads((p/'flash/service/process.json').read_bytes())}
proof={}
for name,saved in records.items():
 v=actual(saved);assert v['uid']==1033
 locks=[]
 for row in lease['lock_records']:
  fd=Path('/proc',str(v['pid']),'fd',str(row['fd']));info=Path('/proc',str(v['pid']),'fdinfo',str(row['fd'])).read_text()
  assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and'WRITE '+str(lease['holder']['pid'])in info
  locks.append({**row,'actual_fdinfo':info})
 assert len(locks)==17;proof[name]={'actual':v,'held_inherited_locks':locks}
cards={}
for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
 i,u,m=[v.strip()for v in line.split(',')];cards[int(i)]={'uuid':u,'free_mib':int(m)}
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
 if line.strip():
  u,pid,m=[v.strip()for v in line.split(',')];compute.append({'uuid':u,'pid':int(pid),'used_mib':m})
for row in lease['gpu']:
 i=row['index'];assert cards[i]['uuid']==row['uuid']
 assert{v['pid']for v in compute if v['uuid']==row['uuid']}=={records['Flash'if i==7 else'primary']['pid']}
requests=[]
for folder in [o/'primary/requests',p/'flash/service/requests']:
 complete=sorted(q for q in folder.iterdir()if q.is_dir()and(q/'response.json').exists()and(q/'seal.json').exists())
 for q in complete[-1:]:
  seal=json.loads((q/'seal.json').read_bytes());assert all(sha(q/n)==h for n,h in seal.items())
  response=json.loads((q/'response.json').read_bytes());requests.append({'folder':str(q),'seal_sha256':sha(q/'seal.json'),'request_id':response['request_id']})
logs={str(q):{'sha256':sha(q),'bytes':q.stat().st_size}for q in[o/'primary.log',o/'Flash-service.log']}
print(json.dumps({'time':time.time(),'ownership':proof,'lease_sha256':sha(o/'lease.json'),'cards':cards,'compute':compute,'logs':logs,'latest_complete_requests':requests,'new_model_GUI_calls':0}))
'''

if __name__ == '__main__':
    m = manifest()
    prefix = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\nMANIFEST=' + repr(sha(__import__('control').PACKAGE / 'manifest.json')) + '\n'
    raw, operation = remote('3090', prefix + CODE, 'trusted-protocol-actual-owned-runtime')
    value = json.loads(raw)
    root = HERE / ('runtime-evidence-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {'operation': str(operation), 'result': value})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), 'actual_processes': {k: {'pid': v['actual']['pid'], 'uid': v['actual']['uid'], 'held_inherited_locks': len(v['held_inherited_locks'])} for k, v in value['ownership'].items()}, 'no_foreign_compute': True, 'new_model_GUI_calls': 0}))
