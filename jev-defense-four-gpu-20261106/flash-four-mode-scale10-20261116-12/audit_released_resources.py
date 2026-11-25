"""Read-only postexit UUID/lock/process verification for this fresh lease."""
import json
import time
from pathlib import Path

from control import HERE, manifest, remote, save, sha


CODE = r'''
import json,os,sys,time
from pathlib import Path
p=Path(P);o=Path(O)
sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot
lease=json.loads((o/'lease.json').read_bytes())
released=json.loads((o/'released.json').read_bytes())
assert released['fresh_lease_locks_closed']==17 and released['no_broker_left_running']
locks=Path('/proc/locks').read_text().splitlines()
held=[]
for record in lease['lock_records']:
 q=Path(record['path']);st=q.stat()
 assert st.st_ino==record['inode']
 device=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)
 matches=[]
 for line in locks:
  fields=line.split()
  for item in fields:
   parts=item.split(':')
   if len(parts)!=3:continue
   try:key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
   except ValueError:continue
   if key==device:matches.append(line)
 held.append({'path':str(q),'inode':st.st_ino,'matching_kernel_locks':matches})
assert not any(row['matching_kernel_locks'] for row in held)
saved=[lease['holder'],json.loads((o/'primary/process.json').read_bytes()),json.loads((p/'flash/service/process.json').read_bytes())]
identities=[]
for row in saved:
 proc=Path('/proc',str(row['pid']));now=None
 if proc.exists():
  stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
  now={'pid':row['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':stat[19],'state':stat[0]}
 same=now is not None and now['state']not in['Z','X']and all(now[k]==row[k]for k in['uid','command','start_ticks'])
 assert not same
 identities.append({'saved':row,'current_if_PID_exists':now,'same_live_process':False})
snapshot=gpu_snapshot()
assert not any(row.get('pid')in{v['pid']for v in saved}for row in snapshot['compute'])
print(json.dumps({'time':time.time(),'released':released,'original_identities':identities,'kernel_lock_records':held,'GPU_snapshot':snapshot,'all_17_kernel_locks_absent':True,'all_original_identities_exited':True,'read_only_no_new_lock_or_GPU_allocation':True,'new_model_GUI_calls':0}))
'''


def main():
    assert not (HERE / 'resource-release-audit-current.json').exists()
    group = json.loads((HERE / 'completed-group-audit-current.json').read_bytes())
    group_root = Path(group['root'])
    assert sha(group_root / 'seal.json') == group['seal_sha256']
    assert json.loads((group_root / 'summary.json').read_bytes())['all_model_GUI_launcher_processes_verified_exited']
    m = manifest()
    raw, operation = remote('3090', 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\n' + CODE,
                            'new-protocol-postexit-kernel-locks-and-GPUs')
    root = HERE / ('resource-release-audit-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {'operation': str(operation), 'group_audit_seal_sha256': group['seal_sha256'],
                                **json.loads(raw)})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'resource-release-audit-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'original_processes_exited': True, 'all_17_kernel_locks_absent': True,
                      'new_resource_allocation': False}))


if __name__ == '__main__':
    main()
