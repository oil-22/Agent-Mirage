"""Read-only mount capacity/ownership inspection; no allocation or eviction."""
import json
from pathlib import Path
import time

from orchestrate import HERE, COMMON, remote, save, sha


def main():
    pointer = HERE / 'persistent-storage-inspection-created.json'
    assert not pointer.exists()
    out = HERE / ('persistent-storage-inspection-' + str(time.time_ns()))
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    operations, values = {}, {}
    for host in ['3090', '4090']:
        code = COMMON + r'''
import re
records=[]
for line in Path('/proc/self/mountinfo').read_text().splitlines():
 left,right=line.split(' - ',1);fields=left.split();suffix=right.split()
 if suffix[0] not in ['ext4','xfs','btrfs','nfs','nfs4','fuse.sshfs']:continue
 target=re.sub(r'\\([0-7]{3})',lambda match:chr(int(match.group(1),8)),fields[4])
 records.append({'mountpoint':target,'fstype':suffix[0],'source':suffix[1],'mount_options':fields[5]})
paths=sorted(set([row['mountpoint']for row in records]+['/home/researcher','/data/researcher','/data','/mnt','/srv']))
stats=[]
for name in paths:
 p=Path(name)
 if not p.is_dir():continue
 try:
  st=p.stat();v=os.statvfs(str(p))
  stats.append({'path':str(p),'resolved':str(p.resolve()),'device':st.st_dev,'uid':st.st_uid,'gid':st.st_gid,
   'access_write_and_search':os.access(str(p),os.W_OK|os.X_OK),'total_bytes':v.f_blocks*v.f_frsize,
   'available_bytes':v.f_bavail*v.f_frsize,'filesystem_read_only':bool(v.f_flag&os.ST_RDONLY)})
 except OSError as error:stats.append({'path':name,'error_type':type(error).__name__,'error':str(error)})
print(json.dumps({'time':time.time(),'actual_uid':os.getuid(),'mounts':records,'paths':stats,
 'new_storage_lease_or_writes_performed':False,'existing_files_read_recursively':False,
 'original_files_deleted_moved_compressed':False,'new_model_GUI_scorer_calls':0}))
'''
        compile(code, 'readonly-persistent-mount-capacity', 'exec')
        output, operation = remote(host, code, 'read-only-persistent-storage-candidates-no-allocation-' + host, timeout=55)
        value = json.loads(output)
        assert value['actual_uid'] == (1033 if host == '3090' else 1015)
        values[host], operations[host] = value, str(operation)
        save(out / (host + '.json'), value)
    save(out / 'receipt.json', dict(time=time.time(), read_only=True, operations=operations,
        whole32storage_fit_or_allocation_proven=False, runtime_modified=False,
        original_files_deleted_moved_compressed=False, new_model_GUI_scorer_calls=0))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(pointer, result)
    print(json.dumps(dict(result, hosts={host: value['paths'] for host,value in values.items()})))


if __name__ == '__main__':
    main()
