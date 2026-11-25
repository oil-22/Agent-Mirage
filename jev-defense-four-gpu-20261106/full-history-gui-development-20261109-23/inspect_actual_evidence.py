"""Read-only live identity, ownership, source, request-seal and chain evidence."""
import json
from pathlib import Path
import time
from remote_control import remote, save, sha, ROOT3090, ROOT4090

HERE = Path(__file__).resolve().parent

COMMON = r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
def chain(p):
 previous='0'*64;counts={};n=0;raw=p.read_bytes();incomplete=bool(raw and not raw.endswith(b'\n'))
 lines=raw.splitlines();lines=lines[:-1]if incomplete else lines
 for line in lines:
  value=json.loads(line);sig=value.pop('sha256')
  assert value['seq']==n and value['previous']==previous
  assert hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sig
  previous=sig;n+=1;counts[value['kind']]=counts.get(value['kind'],0)+1
 return {'events':n,'head':previous,'counts':counts,'incomplete_last_line':incomplete}
'''


def main():
    target = HERE / ('actual-evidence-' + str(time.time_ns()))
    target.mkdir()
    expected = sha(HERE / 'runtime-package/manifest.json')
    code = 'ROOT=' + repr(ROOT3090) + '\nEXPECTED=' + repr(expected) + '\n' + COMMON + r'''
r=Path(ROOT);package=r.parent/'runtime-preparation'/r.name
assert os.getuid()==1033 and sha(package/'manifest.json')==EXPECTED
m=json.loads((package/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(package/name)==h,name
out={'time':time.time(),'read_only':True,'new_model_GUI_scorer_calls':0,'manifest_sha256':EXPECTED,'source_files_verified':len(m['files'])}
lease=json.loads((r.parent/'resource-attempt-20261106-01/lease.json').read_bytes());holder=lease['holder'];actual=identity(holder['pid'])
assert all(str(actual[k])==str(holder[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
locks=[]
for row in lease['lock_records']:
 p=Path('/proc',str(holder['pid']));fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(holder['pid'])in info
 locks.append({'path':row['path'],'fd':row['fd'],'inode':row['inode']})
assert len(locks)==9 and {row['index']for row in lease['gpu']}=={4,5,6,7}
out.update(holder=actual,held_locks=locks,authorized_GPUs=[4,5,6,7])
for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/ready.json','worker/loaded.json','worker/terminal.json','exit.json']:
 p=r/name
 if not p.is_file():continue
 v=json.loads(p.read_bytes())
 if name.endswith('process.json'):
  now=identity(v['pid'])
  if not now.get('absent')and now['state']not in ['Z','X']:assert all(str(v[k])==str(now[k])for k in ['pid','uid','command','start_ticks'])
  v={'record':v,'actual':now}
 if name=='worker/loaded.json':v={k:x for k,x in v.items()if k not in ['actual_cuda_tensors']}
 out[name]={'sha256':sha(p),'value':v}
out['chains']=[dict(path=p.relative_to(r).as_posix(),**chain(p))for p in sorted(r.rglob('events.jsonl'))]
sealed=[]
for p in sorted((r/'worker/requests').glob('*/seal.json')):
 bindings=json.loads(p.read_bytes())
 for name,h in bindings.items():assert sha(p.parent/name)==h,str(p.parent/name)
 ext=json.loads((p.parent/'external-wire.json').read_bytes())
 row={'request':p.parent.name,'operation':'evidence'if 'image_base64'in ext['payload']else ext['payload'].get('operation'),
      'trajectory_id':ext['trajectory_id'],'decision_index':ext['decision_index'],'seal_sha256':sha(p),'files_verified':len(bindings)}
 q=p.parent/'actual-generation.json'
 if q.is_file():
  v=json.loads(q.read_bytes());row['generation']={k:v[k]for k in ['input_tokens','output_tokens','natural_EOS','actual_forward_calls']}
 for name in ['failure.json','contract-failure.json','stateless-boundary.json']:
  q=p.parent/name
  if q.is_file():row[name]={'sha256':sha(q),'value':json.loads(q.read_bytes())}
 sealed.append(row)
out['sealed_requests']=sealed
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
out['GPU_snapshot']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
target_uuids={row['uuid']for row in lease['gpu']};compute=[]
for line in out['compute'].splitlines():
 if not line.strip():continue
 uuid,pid,used=[part.strip()for part in line.split(',')]
 if uuid in target_uuids:compute.append({'GPU_uuid':uuid,'used_MiB':used,'actual_process':identity(int(pid))})
out['authorized_GPU_actual_compute_processes']=compute
disk=shutil.disk_usage(r);out['filesystem']={'free_bytes':disk.free,'total_bytes':disk.total}
for name in ['worker.log','terminal-manifest.json']:
 p=r/name
 if p.is_file():out[name]={'sha256':sha(p),'bytes':p.stat().st_size}
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'actual-service-locks-sealed-requests-no-probe', timeout=55)
    primary = json.loads(output)
    save(target / '3090.json', dict(primary, operation=str(operation)))
    code = 'ROOT=' + repr(ROOT4090) + '\nEXPECTED=' + repr(expected) + '\n' + COMMON + r'''
r=Path(ROOT);assert os.getuid()==1015 and sha(r/'manifest.json')==EXPECTED
m=json.loads((r/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(r/name)==h,name
out={'time':time.time(),'read_only':True,'new_model_GUI_scorer_calls':0,'manifest_sha256':EXPECTED}
for name in ['background/launch.json','control/process.json','control/runner-process.json','control/exit.json','batch/status.json']:
 p=r/name
 if not p.is_file():continue
 v=json.loads(p.read_bytes());record=v.get('identity')if name=='background/launch.json'else v if name.endswith('process.json')else None
 if record:
  now=identity(record['pid'])
  if not now.get('absent')and now['state']not in ['Z','X']:assert all(str(record[k])==str(now[k])for k in ['pid','uid','command','start_ticks'])
  v={'record':v,'actual':now}
 out[name]={'sha256':sha(p),'value':v}
out['chains']=[dict(path=p.relative_to(r).as_posix(),**chain(p))for p in sorted((r/'batch').rglob('events.jsonl'))]
out['terminals']=[]
for p in sorted((r/'batch/runs').glob('*/attempt-*/*.json')):
 if p.name in ['complete.json','technical-failure.json','failure.json','paused.json']:
  v=json.loads(p.read_bytes());v.pop('calls',None)
  out['terminals'].append({'path':p.relative_to(r).as_posix(),'sha256':sha(p),'value':v})
disk=shutil.disk_usage(r);out['filesystem']={'free_bytes':disk.free,'total_bytes':disk.total}
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('4090', code, 'actual-GUI-source-process-and-chain-no-probe', timeout=55)
    gui = json.loads(output)
    save(target / '4090.json', dict(gui, operation=str(operation)))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    print(json.dumps({'evidence': str(target), 'service_state': primary.get('worker/status.json', {}).get('value'),
        'actual_worker': primary.get('worker/process.json', {}).get('value'),
        'actual_launcher': primary.get('launcher-process.json', {}).get('value'),
        'held_locks': len(primary['held_locks']), 'sealed_requests': len(primary['sealed_requests']),
        'service_chains': primary['chains'], 'GUI_state': gui.get('batch/status.json', {}).get('value'),
        'actual_GUI_runner': gui.get('control/runner-process.json', {}).get('value'), 'GUI_chains': gui['chains'],
        'service_free_disk_bytes': primary['filesystem']['free_bytes'], 'GUI_free_disk_bytes': gui['filesystem']['free_bytes'],
        'new_model_GUI_scorer_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
