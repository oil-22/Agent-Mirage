"""Read-only storage inventory for this running experiment; no data eviction."""
import json
from pathlib import Path
import time

from orchestrate import COMMON, HERE, OUTPUT, remote, save, sha


def main():
    code = 'ROOT=' + repr(OUTPUT) + '\n' + COMMON + r'''
import collections
root=Path(ROOT)
process=json.loads((root/'worker/process.json').read_bytes())
actual=identity(process['pid'])
assert not actual.get('absent') and actual['state'] not in ['Z','X']
assert all(str(actual[k])==str(process[k])for k in ['pid','uid','command','start_ticks'])
filesystems=[]
for name in ['/home/researcher','/data/researcher','/tmp']:
 path=Path(name)
 if path.exists():
  stat=path.stat();space=os.statvfs(str(path))
  filesystems.append({'path':str(path),'device':stat.st_dev,
   'total_bytes':space.f_blocks*space.f_frsize,
   'available_bytes':space.f_bavail*space.f_frsize})
by_request=[]
for folder in sorted((root/'worker/requests').iterdir()):
 if not folder.is_dir():continue
 names=list(folder.iterdir())
 total=sum(p.stat().st_size for p in names if p.is_file())
 tensor_bytes=sum(p.stat().st_size for p in names if p.is_file()and p.suffix=='.tensor')
 by_request.append({'request':folder.name,'sealed':(folder/'seal.json').is_file(),
  'all_file_bytes':total,'tensor_bytes':tensor_bytes,
  'file_count':sum(p.is_file()for p in names)})
request_bytes=sum(row['all_file_bytes']for row in by_request)
print(json.dumps({'schema':'GUI32-read-only-owned-output-storage-v1','time':time.time(),
 'actual_worker':actual,'filesystems':filesystems,'requests':by_request,
 'current_request_files_total_bytes':request_bytes,
 'current_tensor_files_total_bytes':sum(row['tensor_bytes']for row in by_request),
 'metadata_size_snapshot_not_a_model_fit_or_future_usage_proof':True,
 'original_files_deleted_moved_compressed':False,
 'new_model_GUI_scorer_calls':0}))
'''
    compile(code, 'owned-output-storage-read-only', 'exec')
    output, operation = remote('3090', code, 'inspect-owned-output-storage-no-eviction', timeout=55)
    value = json.loads(output)
    out = HERE / ('storage-inspection-' + str(time.time_ns()))
    out.mkdir()
    value['remote_operation'] = str(operation)
    save(out / 'receipt.json', value)
    save(out / 'seal.json', {'receipt.json': sha(out / 'receipt.json')})
    print(json.dumps({'root':str(out),'seal_sha256':sha(out/'seal.json'),
        'filesystems':value['filesystems'],
        'current_request_files_total_bytes':value['current_request_files_total_bytes'],
        'current_tensor_files_total_bytes':value['current_tensor_files_total_bytes'],
        'sealed_requests':sum(row['sealed']for row in value['requests']),
        'new_model_GUI_scorer_calls':0},ensure_ascii=False))


if __name__ == '__main__':
    main()
