"""Read-only admission check; never submit, reserve GPUs, or start a worker."""
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, remote, save, sha
from join_reviewed_results import verify

CODE = r'''
import json,os,sys,time
from pathlib import Path
p=Path(P);out=Path(O);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha,gpu_snapshot,identity
assert sha(p/'manifest.json')==EXPECTED
existing=[str(q)for q in[p/'background/launch.json',out/'launcher-process.json',out/'lease.json',out/'exit.json']if q.exists()]
if existing:
 records={};actual=[]
 for q in[out/'launcher-process.json',out/'primary/process.json',p/'flash/service/process.json']:
  if q.exists():
   saved=json.loads(q.read_bytes());v=identity(saved['pid']);records[str(q)]=saved
   actual.append({'record':str(q),'actual':v,'same_original_identity':v is not None and all(v.get(k)==saved.get(k)for k in['uid','command','start_ticks'])})
 print(json.dumps({'time':time.time(),'state':'existing_launch_evidence_inspect_runtime_do_not_submit','existing_receipts':existing,'records':records,'actual':actual,'eligible_for_first_submission':False,'new_GPU_lease':False,'new_model_GUI_calls':0}))
else:
 from continuation_guard import verify_native_parent
 proof=verify_native_parent(p)
 snapshot=gpu_snapshot();m=json.loads((p/'manifest.json').read_bytes())
 for name,digest in m['files'].items():assert sha(p/name)==digest,name
 # Kernel locks are examined without opening lock files for writing or flock.
 paths=[]
 paths.append('/home/researcher/.mirage-resource-locks/jev-flash-four-mode-scale10-20261117-linked13.lock')
 for row in snapshot['gpu'].values():
  paths.extend(['/home/researcher/.mirage-resource-locks/'+row['uuid']+'.lock',
                '/home/researcher/defense-resume-20261102-retry2/resource-locks/'+row['uuid']+'.lock'])
 lines=Path('/proc/locks').read_text().splitlines();locks=[]
 for name in paths:
  q=Path(name);matches=[]
  if q.exists():
   st=q.stat();wanted=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)
   for line in lines:
    for field in line.split():
     parts=field.split(':')
     if len(parts)!=3:continue
     try:key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
     except ValueError:continue
     if key==wanted:matches.append(line)
  locks.append({'path':name,'exists':q.exists(),'kernel_locks':matches})
 stat=os.statvfs(str(out.parent.parent));available=stat.f_bavail*stat.f_frsize
 ready=not snapshot['compute']and all(snapshot['gpu'][i]['free_mib']>=23000 for i in range(8))and not any(v['kernel_locks']for v in locks)and available>64*1024**3
 print(json.dumps({'time':time.time(),'state':'eligible_for_fresh_submission'if ready else'waiting_exclusive_eight_GPUs',
  'manifest_sha256':EXPECTED,'snapshot':snapshot,'kernel_locks':locks,'output_disk_available_bytes':available,
  'parent_proof':proof,'eligible_for_first_submission':ready,'submit_must_recheck_and_inherit_owned_locks':True,
  'new_GPU_lease':False,'new_model_GUI_calls':0}))
'''


def main():
    prep = json.loads((HERE / 'preparation-current.json').read_bytes())
    qualification = json.loads((HERE / 'CPU-routing-current.json').read_bytes())
    verify(qualification['root'], qualification['seal_sha256'])
    assert qualification['passed'] and qualification['manifest_sha256'] == prep['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    for host in ['3090', '4090']:
        staged = json.loads((HERE / ('stage-' + host + '.json')).read_bytes())
        assert staged['result']['manifest_sha256'] == prep['manifest_sha256']
    m = manifest()
    raw, operation = remote('3090', 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090'])
        + '\nEXPECTED=' + repr(prep['manifest_sha256']) + '\n' + CODE, 'linked26-readonly-admission-wait')
    value = json.loads(raw)
    root = HERE / ('resource-admission-check-' + str(time.time_ns())); root.mkdir()
    save(root / 'result.json', {'operation': str(operation), 'result': value})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}
    temp = HERE / ('.resource-admission-' + str(time.time_ns())); save(temp, pointer)
    temp.replace(HERE / 'resource-admission-current.json')
    snapshot = value.get('snapshot', {})
    print(json.dumps({'root': str(root), 'state': value['state'],
        'eligible_for_first_submission': value['eligible_for_first_submission'],
        'empty_GPUs': [i for i, card in snapshot.get('gpu', {}).items()
                       if card['free_mib'] >= 23000 and not any(r['uuid'] == card['uuid'] for r in snapshot['compute'])],
        'foreign_UIDs': sorted({r['identity']['uid'] for r in snapshot.get('compute', [])}),
        'new_GPU_lease': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
