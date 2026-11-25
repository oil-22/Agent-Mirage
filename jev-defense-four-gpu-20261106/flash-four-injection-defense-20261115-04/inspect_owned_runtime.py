"""Read-only actual process/UUID/inherited-lock/log/request evidence."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import hashlib,json,os,subprocess,time
from pathlib import Path
p=Path(P);out=Path(O)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def identity(pid):
 q=Path('/proc',str(pid));s=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
original_path=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
original=json.loads(original_path.read_bytes());expanded=json.loads((out/'expanded-lease.json').read_bytes())
records={'original_holder':original['holder'],'launcher':expanded['holder'],'primary':json.loads((out/'primary/process.json').read_bytes()),'Flash':json.loads((p/'flash/service/process.json').read_bytes())}
actual={};held={}
for name,saved in records.items():
 current=identity(saved['pid']);assert current['state']not in ['Z','X']and all(current[k]==saved[k]for k in ['pid','uid','command','start_ticks'])
 actual[name]=current
 rows=original['lock_records']+(expanded['extra_lock_records']if name in ['launcher','primary']else[])
 checked=[]
 for row in rows:
  fd=Path('/proc',str(saved['pid']),'fd',str(row['fd']));info=(fd.parent.parent/'fdinfo'/str(row['fd'])).read_text()
  holder=original['holder']if row in original['lock_records']else expanded['holder']
  assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and'WRITE '+str(holder['pid'])in info
  checked.append({'path':row['path'],'fd':row['fd'],'inode':row['inode'],'actual_fdinfo':info})
 held[name]=checked
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
 if line.strip():
  uuid,pid,used=[s.strip()for s in line.split(',')];compute.append({'uuid':uuid,'identity':identity(pid),'used_MiB':used})
expected={actual['primary']['pid'],actual['Flash']['pid']};foreign=[v for v in compute if v['identity']['pid']not in expected]
logs=[]
for file in [out/'primary.log',out/'Flash-service.log']:
 raw=file.read_bytes();logs.append({'path':str(file),'prefix_bytes':len(raw),'prefix_sha256':hashlib.sha256(raw).hexdigest()})
recent=[]
for kind,folder in [('primary',out/'primary/requests'),('Flash',p/'flash/service/requests')]:
 completed=[q for q in folder.iterdir()if(q/'seal.json').exists()and(q/'response.json').exists()]
 if not completed:continue
 q=max(completed,key=lambda q:(q/'response.json').stat().st_mtime_ns)
 for name in ['wire-request.bin','response.json']:
  seal=json.loads((q/'seal.json').read_bytes());assert sha(q/name)==seal[name]
 response=json.loads((q/'response.json').read_bytes())
 recent.append({'kind':kind,'request':str(q),'request_id':response['request_id'],'wire_sha256':sha(q/'wire-request.bin'),'response_sha256':sha(q/'response.json'),'seal_sha256':sha(q/'seal.json')})
print(json.dumps({'time':time.time(),'actual':actual,'held_inherited_locks':held,'compute':compute,'foreign_compute_not_preempted':foreign,'log_prefixes':logs,'recent_complete_actual_request_response':recent,'new_model_GUI_calls':0}))
'''


def main():
    m = manifest()
    raw, operation = remote('3090', 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\n' + CODE, 'verify-actual-runtime-locks-request-logs')
    value = json.loads(raw)
    root = HERE / ('runtime-evidence-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {'operation': str(operation), 'result': value})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'root': str(root), 'actual': value['actual'],
                      'held_lock_counts': {k: len(v) for k, v in value['held_inherited_locks'].items()},
                      'foreign_compute': value['foreign_compute_not_preempted'],
                      'recent_requests': value['recent_complete_actual_request_response']}))


if __name__ == '__main__':
    main()
