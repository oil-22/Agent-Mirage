"""Read owned storage headroom and actual receipt sizes without moving files."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


CODE = r'''
from pathlib import Path
import json,os,time
root=Path('/home/researcher/jev-defense-four-gpu-20261106/prefill-scheduled-full-history-gui-20261109-32')
pid=4108313;proc=Path('/proc',str(pid))
assert proc.stat().st_uid==1033
command=(proc/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()
assert '/runtime-preparation/prefill-scheduled-full-history-gui-20261109-32/gpu_server.py --manifest 'in command
assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]=='1184962121'
paths=[]
for name in ['/home/researcher','/data/researcher','/mnt','/tmp']:
 p=Path(name)
 if not p.exists():continue
 v=os.statvfs(p)
 paths.append({'path':name,'resolved':str(p.resolve()),'device':p.stat().st_dev,'owner_UID':p.stat().st_uid,
  'current_UID_write_access':os.access(p,os.W_OK),'available_bytes':v.f_bavail*v.f_frsize,
  'total_bytes':v.f_blocks*v.f_frsize})
requests=[]
for p in sorted((root/'worker/requests').iterdir()):
 if not p.is_dir():continue
 files=[q for q in p.rglob('*')if q.is_file()]
 row={'request':p.name,'bytes_at_snapshot':sum(q.stat().st_size for q in files),'files':len(files),'sealed':(p/'seal.json').is_file()}
 if (p/'payload.json').is_file():row['operation']=json.loads((p/'payload.json').read_bytes()).get('operation')
 if (p/'actual-generation.json').is_file():
  data=json.loads((p/'actual-generation.json').read_bytes());row.update(input_tokens=data['input_tokens'],output_tokens=data['output_tokens'])
 requests.append(row)
print(json.dumps({'time':time.time(),'read_only':True,'actual_worker':{'pid':pid,'UID':1033,'command':command,'start_ticks':'1184962121'},
 'storage':paths,'requests':requests,'raw_request_bytes_at_snapshot':sum(r['bytes_at_snapshot']for r in requests),
 'no_files_moved_deleted_compressed_or_changed':True,'new_model_GUI_scorer_calls':0},ensure_ascii=False))
'''


if __name__ == '__main__':
    assert not (HERE / 'storage-inspection-created.json').exists()
    output, operation = remote('3090', CODE, 'read-owned-storage-and-actual-request-sizes-no-file-moves', timeout=55)
    result = json.loads(output)
    out = HERE / ('storage-inspection-' + str(time.time_ns()))
    out.mkdir()
    result['remote_operation'] = str(operation)
    save(out / 'inspection.json', result)
    save(out / 'seal.json', {'inspection.json': sha(out / 'inspection.json')})
    save(HERE / 'storage-inspection-created.json', {'inspection': str(out / 'inspection.json'), 'sha256': sha(out / 'inspection.json')})
    print(json.dumps(result, ensure_ascii=False))
