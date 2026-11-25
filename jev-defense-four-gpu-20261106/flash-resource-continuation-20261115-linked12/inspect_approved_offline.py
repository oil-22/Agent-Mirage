"""Read the one approved offline run without launching or retrying anything."""
import json
import time
from pathlib import Path

from control import HERE, remote, save, sha
from capture_live_evidence import COMMON
from offline_followup_control import OUTPUT, REMOTE, PREP


def main():
    submission = PREP / 'submission.json'
    assert submission.exists(), 'Inspect only the already submitted ten-call run'
    code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE)
            + '\nEXPECTED=' + repr(sha(PREP / 'package/offline-manifest.json'))
            + '\n' + COMMON + r'''
import subprocess
r=Path(ROOT);p=Path(PACKAGE)
assert sha(p/'offline-manifest.json')==EXPECTED
out={'time':time.time(),'output_exists':r.exists(),'new_model_GPU_GUI_calls':0,
     'processes':{},'complete_replies':[],'full_raw_input_reaudit_claimed':False}
for label,name in [('launcher','launcher-process.json'),('worker','worker/process.json')]:
 f=r/name
 if not f.exists():continue
 saved=json.loads(f.read_bytes());proc=Path('/proc',str(saved['pid']))
 actual=identity(saved['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['pid','uid','command','start_ticks'])
 if actual is not None and actual['state']not in ['Z','X']:assert same,'A saved PID was reused; no process action allowed'
 assert saved['uid']==1033
 out['processes'][label]={'saved':saved,'actual':actual,'same_live':same}
leasefile=r/'offline-lease.json'
if leasefile.exists():
 lease=json.loads(leasefile.read_bytes())
 # Obtain the exact original lease path from the frozen guard source rather
 # than assuming its basename when deployment layouts differ.
 import sys
 sys.path.insert(0,str(p));import offline_guard as guard
 old=json.loads(guard.LEASE.read_bytes())
 records=old['lock_records']+lease['extra_lock_records']+[lease['inference_lock_record']]
 worker=out['processes'].get('worker',{})
 if worker.get('same_live'):
  proc=Path('/proc',str(worker['actual']['pid']));held=[]
  for row in records:
   fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
   assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']
   assert 'FLOCK'in info and 'WRITE'in info
   held.append({'path':row['path'],'fd':row['fd'],'inode':row['inode']})
  out['actual_worker_inherited_held_locks']=held
 out['lease_sha256']=sha(leasefile)
 out['reserved_GPU_count']=lease['actually_reserved_GPUs_including_idle7']
 assert out['reserved_GPU_count']==8
for name in ['worker/loaded.json','worker/terminal.json','worker/failure.json','exit.json','launcher-failure.json']:
 f=r/name
 if f.exists():out[name]=json.loads(f.read_bytes())
for d in sorted((r/'worker/requests').glob('*')):
 if not(d/'seal.json').exists()or not(d/'response.json').exists():continue
 seal=json.loads((d/'seal.json').read_bytes())
 assert sha(d/'response.json')==seal['response.json']
 reply=json.loads((d/'response.json').read_bytes())
 out['complete_replies'].append({'case':reply['case'],'seal_sha256':sha(d/'seal.json'),
  'response_sha256':sha(d/'response.json'),'native_response_not_executed':reply['proposed_action_not_executed']})
assert len(out['complete_replies'])<=10
journal=r/'worker/journal/events.jsonl'
if journal.exists():out['journal'],events=chain(journal)
out['postexit_seal_exists']=(r/'postexit-seal.json').exists()
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).strip()
out['compute']=[]
raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits'],text=True).strip()
worker=out['processes'].get('worker',{})
for line in raw.splitlines():
 uuid,pid,memory=[v.strip()for v in line.split(',')];actual=identity(int(pid))
 out['compute'].append({'uuid':uuid,'memory_MiB':memory,'actual':actual,
  'matches_current_worker':bool(worker.get('same_live')and all(actual[k]==worker['actual'][k]for k in ['pid','uid','command','start_ticks']))})
log=r/'worker.log'
if log.exists():out['worker_log_sha256']=sha(log);out['worker_log_tail']=log.read_text(errors='replace')[-1400:]
print(json.dumps(out))
''')
    raw, operation = remote('3090', code, 'actual-approved10-worker-lock-GPU-request-inspection')
    result = json.loads(raw)
    dest = HERE / ('approved10-activity-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'activity.json', {'result': result, 'operation': str(operation),
         'submission': str(submission), 'submission_sha256': sha(submission)})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'activity': str(dest), 'processes': result['processes'],
        'complete_reply_cases': [v['case'] for v in result['complete_replies']],
        'actual_worker_lock_count': len(result.get('actual_worker_inherited_held_locks', [])),
        'compute_processes': result['compute'], 'postexit_seal_exists': result['postexit_seal_exists'],
        'terminal': result.get('worker/terminal.json'), 'failure': result.get('worker/failure.json'),
        'new_model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
