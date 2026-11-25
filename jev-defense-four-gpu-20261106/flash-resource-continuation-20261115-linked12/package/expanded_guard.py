"""Verify original nine locks and eight newly inherited UUID locks; never preempt."""
import json,os,time
from pathlib import Path
from resource_guard import locks,identity,sha,gpu_snapshot

def validate_compute(cards,compute,expected):
    for index,pid in expected.items():
        pids={r['pid']for r in compute if r['uuid']==cards[index]['uuid']}
        if pids!=({pid}if pid is not None else set()):
            # Preserve the already captured actual UID/full command/UUID snapshot before rejecting.
            root=Path(os.environ['MIRAGE_RESOURCE_FORENSICS_ROOT']);root.mkdir(parents=True,exist_ok=True)
            path=root/(str(time.time_ns())+'.json')
            with path.open('x',encoding='utf8')as f:
                json.dump({'time':time.time(),'GPU':index,'cards':cards,'compute':compute,'expected':expected,'not_model_NO':True,'no_automatic_retry':True},f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
            raise RuntimeError('Foreign/unverified compute on GPU '+str(index)+': '+str(pids))

def expanded_locks():
    old,fds=locks();path=Path(os.environ['MIRAGE_EXPANDED_LEASE'])
    if sha(path)!=os.environ['MIRAGE_EXPANDED_LEASE_SHA256']:raise RuntimeError('Expanded lease changed')
    lease=json.loads(path.read_bytes());h=lease['holder'];a=identity(h['pid'])
    if any(a[k]!=h[k]for k in ['uid','command','start_ticks'])or a['state']in ['Z','X']:raise RuntimeError('Expanded holder identity changed')
    extra=tuple(int(x)for x in os.environ['MIRAGE_EXTRA_GPU_LOCK_FDS'].split(','))
    if len(extra)!=8 or set(extra)&set(fds):raise RuntimeError('All eight new locks must be inherited separately')
    if tuple(r['fd']for r in lease['extra_lock_records'])!=extra:raise RuntimeError('Extra lock FD set changed')
    for row in lease['extra_lock_records']:
        fd=row['fd'];p=Path('/proc/self')
        if os.fstat(fd).st_ino!=row['inode']or os.readlink(p/'fd'/str(fd))!=row['path']or 'WRITE '+str(h['pid'])not in(p/'fdinfo'/str(fd)).read_text():raise RuntimeError('Expanded actual held lock mismatch')
    return lease,fds+extra

def resource(package,loaded):
    lease,fds=expanded_locks();s=gpu_snapshot();cards=s['gpu']
    for i in range(8):
        if cards[i]['uuid']!=next(v['uuid']for v in lease['gpu']if v['index']==i):raise RuntimeError('Leased UUID changed')
    record=json.loads((package/'flash/service/process.json').read_bytes());actual=identity(record['pid'])
    if any(actual[k]!=record[k]for k in ['uid','command','start_ticks']):raise RuntimeError('Flash ownership changed')
    validate_compute(cards,s['compute'],{**{i:os.getpid()if loaded else None for i in range(7)},7:record['pid']})
    if not loaded and any(cards[i]['free_mib']<23000 for i in range(7)):raise RuntimeError('Insufficient empty owned memory')
    v=os.statvfs(package)
    if v.f_bavail*v.f_frsize<16*1024**3:raise RuntimeError('Storage headroom insufficient; preserve and stop')
    return {'time':s.get('time'),'cards':cards,'compute':s['compute'],'held_inherited_locks':len(fds),'primary_physical_gpus':list(range(7)),'Flash_physical_gpu':7,'expanded_lease_sha256':sha(Path(os.environ['MIRAGE_EXPANDED_LEASE']))}
