import hashlib,json,os,subprocess
from pathlib import Path
B=Path('/home/researcher/jev-defense-four-gpu-20261106')
LEASE=B/'resource-attempt-20261106-01/lease.json'
LEASE_SHA='8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def identity(pid):
    p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
def locks():
    if os.getuid()!=1033 or sha(LEASE)!=LEASE_SHA:raise RuntimeError('Owned task lease identity mismatch')
    lease=json.loads(LEASE.read_bytes());h=lease['holder'];a=identity(h['pid'])
    if any(a[k]!=h[k]for k in ['pid','uid','command','start_ticks'])or a['state']in['Z','X']:raise RuntimeError('Original lock holder not alive')
    fds=tuple(int(s)for s in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    if len(fds)!=9 or os.environ['MIRAGE_TASK_LEASE']!=str(LEASE):raise RuntimeError('Inherited task locks required')
    for row in lease['lock_records']:
        fd=row['fd'];p=Path('/proc/self')
        if fd not in fds or os.fstat(fd).st_ino!=row['inode']or os.readlink(p/'fd'/str(fd))!=row['path']or 'WRITE '+str(h['pid'])not in(p/'fdinfo'/str(fd)).read_text():raise RuntimeError('Actual inherited held lock mismatch')
    return lease,fds
def gpu_snapshot():
    cards={};compute=[]
    for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
        i,u,m=[s.strip()for s in line.split(',')];cards[int(i)]={'uuid':u,'free_mib':int(m)}
    for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
        if line.strip():
            u,p,m=[s.strip()for s in line.split(',')];compute.append({'uuid':u,'pid':int(p),'used_mib':m,'identity':identity(int(p))})
    return {'gpu':cards,'compute':compute}
def admit(config,loaded):
    lease,_=locks();s=gpu_snapshot();index=config['physical_gpu'];uuid=s['gpu'][index]['uuid']
    if index not in [4,5,6,7]or uuid!=next(r['uuid']for r in lease['gpu']if r['index']==index):raise RuntimeError('GPU not part of authorized lease')
    pids={r['pid']for r in s['compute']if r['uuid']==uuid}
    if pids!=({os.getpid()}if loaded else set()):raise RuntimeError('Exclusive GPU unavailable; do not share/preempt: '+str(pids))
    if not loaded and s['gpu'][index]['free_mib']<23000:raise RuntimeError('Insufficient owned free memory')
    return s
def checkpoint(config,root):
    receipt=Path(config['receipt']);stable_path=root/'flash-identity.json'
    if sha(receipt)!=config['receipt_sha256']or sha(stable_path)!=config['stable_identity_sha256']:raise RuntimeError('Model identity receipt mismatch')
    completed=json.loads(receipt.read_bytes());stable=json.loads(stable_path.read_bytes());saved={r['file']:r for r in stable['files']};model=Path(config['model_dir'])
    if completed['revision']!=config['revision']or stable['revision']!=config['revision']:raise RuntimeError('Model revision mismatch')
    rows=[]
    for row in completed['files']:
        p=model/row['file'];s=p.stat();stamp={'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns};old=saved[row['file']]
        if p.is_symlink()or not p.resolve().is_relative_to(model.resolve())or stamp!=old['stat']or s.st_size!=row['bytes']or row['sha256']!=old['sha256']:raise RuntimeError('Checkpoint changed since complete byte verification: '+row['file'])
        if p.suffix!='.safetensors'and sha(p)!=row['sha256']:raise RuntimeError('Native source/metadata hash mismatch')
        rows.append({'file':row['file'],'sha256_from_completed_byte_audit':row['sha256'],'stable_stat':stamp})
    return {'revision':config['revision'],'completion_receipt_sha256':sha(receipt),'stable_identity_sha256':sha(stable_path),'files':rows,'no_redundant_full_weight_rehash':True}
