"""Read/copy-only preservation of an idle technical terminal on both hosts.

No health, HTTP, model calls, GUI, scorer, signal or stop marker is issued.
"""
import concurrent.futures,hashlib,json,subprocess,time
from pathlib import Path

BASE=Path(__file__).resolve().parent
REMOTE=r'''
import hashlib,json,os,shutil,stat,subprocess,time
from pathlib import Path
host=HOST
B=Path('/home/researcher/jev-defense-four-gpu-20261106'if host=='3090'else'/data/researcher/jev-defense-four-gpu-20261106')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  while True:
   block=f.read(4194304)
   if not block:break
   h.update(block)
 return h.hexdigest()
def save(p,x):
 with p.open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2)
 os.chmod(str(p),0o600)
def identity(pid):
 p=Path('/proc')/str(pid);s=(p/'stat').read_text();tail=s[s.rfind(')')+2:].split()
 return{'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().rstrip(b'\0').replace(b'\0',b' ').decode(),
  'start_ticks':tail[19],'state':tail[0]}
def same(expected):
 actual=identity(expected['pid'])
 assert all(str(actual[k])==str(expected[k])for k in('pid','uid','command','start_ticks')),('identity',expected['pid'])
 return actual
def manifest(root):
 d={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():d[str(p.relative_to(root))]={'symlink':os.readlink(str(p))}
  elif p.is_file():d[str(p.relative_to(root))]={'sha256':sha(p),'bytes':p.stat().st_size}
 return d
group=B/'online-three-service-group-1793985778592347799'
rows=[];request_counts={};lease=None
if host=='3090':
 assert os.getuid()==1033
 lease=json.loads((B/'resource-attempt-20261106-01/lease.json').read_bytes())
 for role in('primary','pplx_flash'):
  launch=json.loads((group/(role+'-launch.json')).read_bytes());actual=same(launch['identity'])
  locks=[]
  for expected in lease['lock_records']:
   fd=Path('/proc')/str(actual['pid'])/'fd'/str(expected['fd']);info=Path('/proc')/str(actual['pid'])/'fdinfo'/str(expected['fd'])
   assert str(fd.readlink())==expected['path']and fd.stat().st_ino==expected['inode']and'lock:'in info.read_text()
   locks.append({'fd':expected['fd'],'path':expected['path'],'inode':expected['inode']})
  requests=sorted((group/role/'requests').glob('*'));requests=[p for p in requests if p.is_dir()]
  assert len(requests)==(97 if role=='primary' else 20)
  for request in requests:
   seal=json.loads((request/'seal.json').read_bytes())
   assert all(sha(request/name)==expected for name,expected in seal.items()),str(request)
   assert(request/'response.json').exists()and not(request/'failure.json').exists()
  request_counts[role]={'completed':len(requests),'failed':0,'pending':0}
  rows.append({'role':role,'actual':actual,'held_locks':locks})
 launcher=same(json.loads((group/'process.json').read_bytes()))
 holder=same(lease['holder'])
 state=json.loads((group/'state.json').read_bytes())
 assert state['phase']=='terminal_failure'and state['active']is None
 compute=[]
 for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']).decode().splitlines():
  if line.strip():
   u,p=line.split(',');compute.append({'uuid':u.strip(),'pid':int(p.strip())})
 target_uuids={g['uuid']for g in lease['gpu']};target=[r for r in compute if r['uuid']in target_uuids]
 assert all(r['pid']in[r['actual']['pid']for r in rows]for r in target)
 sources={'service-group':group,
 'online-source':B/'runtime-preparation/gui-three-linked02-1793985778592347799',
 'primary-release':B/'primary-release-01',
 'preflight-source':B/'runtime-preparation/failed-layout-capacity-1793984469336572715'}
 proof={'workers':rows,'launcher':launcher,'holder':holder,'request_counts':request_counts,'state':state,
 'target_compute':target,'foreign_target_compute':[],'all_actual_workers_9locks':all(len(r['held_locks'])==9 for r in rows),'all_pending_zero':True}
else:
 assert os.getuid()==1015
 batch=B/'gui-batch-image-observer-three-01'
 attempt=batch/'runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761'
 assert sha(attempt/'technical-failure.json')=='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
 sources={'GUI-batch':batch,'GUI-control':B/'gui-outer-control-three-01','GUI-background':B/'gui-outer-background-three-01',
 'GUI-package':B/'gui-migration-three-linked02','GUI-readiness':B/'gui-final-readiness-three-01',
 'GUI-evidence-binding':B/'gui-three-evidence-binding-01','GUI-control-preparation':B/'gui-three-control-preparation-01'}
 proof={'terminal_path':str(attempt/'technical-failure.json'),'terminal_sha256':sha(attempt/'technical-failure.json'),
 'technical_terminal':True,'existing_terminal_seals_untouched':True}
assert all(p.is_dir()for p in sources.values())
before={name:manifest(p)for name,p in sources.items()}
total=sum(v.get('bytes',0)for m in before.values()for v in m.values())
root=B/'three-terminal-prestop-preservation'/STAMP
assert not root.exists()
assert shutil.disk_usage(str(B)).free>total+1073741824
root.mkdir(mode=0o700,parents=True,exist_ok=False)
save(root/'source-manifests-before.json',before)
for name,path in sources.items():
 target=root/'snapshot'/name
 target.parent.mkdir(mode=0o700,exist_ok=True)
 shutil.copytree(str(path),str(target),symlinks=True)
 copied=manifest(target)
 assert copied==before[name],('copied_mismatch',name)
 assert manifest(path)==before[name],('original_changed',name)
 for q in target.rglob('*'):
  if not q.is_symlink():os.chmod(str(q),0o700 if q.is_dir() else 0o600)
 os.chmod(str(target),0o700)
if host=='3090':
 for row in rows:same(row['actual'])
 state_after=json.loads((group/'state.json').read_bytes())
 assert state_after==state
 proof['proof_after_copy_time']=time.time()
save(root/'actual-idle-proof.json',proof)
receipt={'status':'prestop_preserved_not_stopped','host':host,'root':str(root),'time':time.time(),
 'source_paths':{k:str(v)for k,v in sources.items()},'copied_files':sum(len(m)for m in before.values()),'copied_regular_bytes':total,
 'original_before_after_and_copy_SHA_equal':True,'actual_proof':str(root/'actual-idle-proof.json'),
 'actual_proof_sha256':sha(root/'actual-idle-proof.json'),'source_manifests_sha256':sha(root/'source-manifests-before.json'),
 'HTTP_model_GUI_scorer_calls':0,'stop_signals_or_marker_writes':0,'private_content_retained_remote_only':True}
save(root/'receipt.json',receipt)
save(root/'preservation-seal.json',manifest(root))
print(json.dumps({'host':host,'root':str(root),'receipt_sha256':sha(root/'receipt.json'),
 'seal_sha256':sha(root/'preservation-seal.json'),'actual_proof_sha256':sha(root/'actual-idle-proof.json'),
 'copied_files':receipt['copied_files'],'copied_bytes':total,'actual_proof':proof,'no_stop_performed':True},ensure_ascii=False))
'''

def run(host,stamp,out):
 argv=[r'D:\Git\usr\bin\ssh.exe','-F',r'C:\Users\researcher\.ssh\config','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3','-']
 code='HOST='+repr(host)+'\nSTAMP='+repr(stamp)+'\n'+REMOTE
 (out/(host+'-source.py')).write_text(code,encoding='utf8')
 try:r=subprocess.run(argv,input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1200)
 except subprocess.TimeoutExpired as e:
  (out/(host+'-timeout.stdout')).write_bytes(e.stdout or b'');(out/(host+'-timeout.stderr')).write_bytes(e.stderr or b'')
  raise
 (out/(host+'-stdout.json')).write_bytes(r.stdout);(out/(host+'-stderr.txt')).write_bytes(r.stderr)
 if r.returncode:raise RuntimeError(host+': '+r.stderr.decode(errors='replace'))
 return json.loads(r.stdout)

if __name__=='__main__':
 stamp=str(time.time_ns());out=BASE/'three-prestop-preservation-invocation'/stamp;out.mkdir(parents=True,exist_ok=False)
 print(json.dumps({'local_invocation':str(out),'stamp':stamp}),flush=True)
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
   fs={host:pool.submit(run,host,stamp,out)for host in('3090','4090')}
   for host,future in fs.items():print(json.dumps(future.result(),ensure_ascii=False),flush=True)
 finally:
  (out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
