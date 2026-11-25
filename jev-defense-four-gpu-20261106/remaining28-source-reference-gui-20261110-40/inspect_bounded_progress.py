"""Read-only bounded inventory after the all-binary inspection timed out.

This observer does not load a model, call a service, operate the GUI, or launch
any experiment. It records incomplete audits explicitly instead of treating
an inventory as full receipt verification.
"""
import argparse
import json
from pathlib import Path
import time

import orchestrate as current


BOUNDED = r'''
def small(path, maximum=4*1024*1024):
 if not path.is_file():return None
 st=path.stat()
 assert st.st_size <= maximum, str(path)
 raw=path.read_bytes()
 return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'value':json.loads(raw)}

def tail(path, maximum=2200):
 if not path.is_file():return None
 with path.open('rb')as stream:
  stream.seek(max(0,path.stat().st_size-maximum));raw=stream.read(maximum)
 return {'bytes':path.stat().st_size,'mtime_ns':path.stat().st_mtime_ns,'tail':raw.decode(errors='replace')}

out={'time':time.time(),'uid':os.getuid(),'host':HOST,'root':ROOT,
 'read_only':True,'model_GUI_scorer_calls_by_observer':0,
 'inventory_only_not_full_SHA_or_chain_verification':True}
r=Path(ROOT)
assert sha(Path(PACKAGE)/'manifest.json')==EXPECTED
out['manifest_sha256']=EXPECTED
if HOST=='3090':
 for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/ready.json','worker/terminal.json','worker/failure.json','exit.json']:
  item=small(r/name)
  if item:
   if name.endswith('process.json'):item['actual']=identity(item['value']['pid'])
   out[name]=item
 leasepath=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
 lease=small(leasepath);h=lease['value']['holder'];actual=identity(h['pid'])
 out['lease_sha256']=lease['sha256'];out['holder_actual']=actual
 out['holder_identity_matches']=not actual.get('absent')and all(str(actual.get(k))==str(h[k])for k in['pid','uid','command','start_ticks'])and actual.get('state')not in['Z','X']
 out['locks']=[]
 for row in lease['value']['lock_records']:
  record={'path':row['path'],'fd':row['fd'],'held':False}
  try:
   proc=Path('/proc',str(h['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
   record.update(actual_path=os.readlink(fd),actual_inode=fd.stat().st_ino,
    held=os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(h['pid'])in info)
  except OSError as exc:record['inspection_error']=type(exc).__name__
  out['locks'].append(record)
 out['requests']=[]
 for p in sorted((r/'worker/requests').glob('*')):
  if not p.is_dir():continue
  item={'request':p.name,'sealed':(p/'seal.json').is_file(),'failed':(p/'failure.json').is_file()}
  if item['sealed']:item['seal_sha256']=sha(p/'seal.json')
  if item['failed']:item['failure']=small(p/'failure.json')
  out['requests'].append(item)
 out['worker_log']=tail(r/'worker.log')
 out['journal']=tail(r/'worker/journal/events.jsonl',1000)
 out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=12)
 out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=12)
 out['compute_identities']=[]
 owned={row['uuid']for row in lease['value']['gpu']}
 for line in out['compute'].splitlines():
  uuid,pid,memory=[v.strip()for v in line.split(',')]
  if uuid in owned:out['compute_identities'].append({'uuid':uuid,'memory_MiB':memory,'actual':identity(int(pid))})
else:
 for name in ['background/launch.json','control/process.json','control/runner-process.json','control/exit.json','batch/status.json','batch/uncaught-failure.json']:
  item=small(r/name)
  if item:
   record=item['value'].get('identity',item['value'])
   if'pid'in record:item['actual']=identity(record['pid'])
   out[name]=item
 out['runs']=[]
 for run in sorted((r/'batch/runs').glob('*')):
  if not run.is_dir():continue
  row={'run_id':run.name,'attempts':[]}
  for attempt in sorted(run.glob('attempt-*')):
   record={'attempt':attempt.name}
   for name in ['complete.json','technical-failure.json','terminal-manifest.json','result.json']:
    item=small(attempt/name)
    if item:record[name]=item
   event=attempt/'events.jsonl'
   if event.is_file():record['events_stat']={'bytes':event.stat().st_size,'mtime_ns':event.stat().st_mtime_ns}
   row['attempts'].append(record)
  out['runs'].append(row)
 out['runner_log']=tail(r/'control/runner.log')
print(json.dumps(out,ensure_ascii=True))
'''


def main(host):
    current.admitted()
    target = current.HERE / ('bounded-progress-' + host + '-' + str(time.time_ns()))
    target.mkdir()
    root = current.OUTPUT if host == '3090' else current.GUIROOT
    package = current.REMOTE_PACKAGE if host == '3090' else current.GUIROOT
    code = ('HOST=' + repr(host) + '\nROOT=' + repr(root) + '\nPACKAGE=' + repr(package)
            + '\nEXPECTED=' + repr(current.sha(current.PACKAGE / 'manifest.json'))
            + '\n' + current.COMMON + BOUNDED)
    try:
        raw, operation = current.remote(host, code, 'bounded-remaining28-progress-read-only-linked-inspection', timeout=50)
        value = json.loads(raw)
        current.save(target / 'inventory.json', value)
        current.save(target / 'operation.json', {'path':str(operation)})
        current.save(target / 'scope.json', {
            'source_sha256':current.sha(Path(__file__)),
            'scope':'read-only inventory; binary receipts and event chains require separate verification',
            'prior_unsealed_inspection_evidence':[str(p) for p in sorted(current.HERE.glob('actual-evidence-*')) if not(p/'seal.json').exists()],
            'prior_inspection_logs':[{ 'path':str(p),'sha256':current.sha(p)}for p in sorted(current.HERE.glob('inspect-console-*'))][-2:],
            'new_model_GUI_scorer_calls':0})
        current.save(target / 'seal.json', {p.name:current.sha(p)for p in target.iterdir()if p.is_file()})
    except Exception as exc:
        current.save(target / 'inspection-failure.json', {'type':type(exc).__name__,'message':str(exc),'model_failure':False})
        raise
    result={'evidence':str(target),'host':host}
    if host=='3090':
        result.update(state=value.get('worker/status.json'),terminal=value.get('worker/terminal.json'),
            exit=value.get('exit.json'),actual_worker=value.get('worker/process.json',{}).get('actual'),
            total_requests=len(value['requests']),sealed_requests=sum(p['sealed']for p in value['requests']),
            failed_requests=[p for p in value['requests']if p['failed']],
            holder_identity_matches=value['holder_identity_matches'],held_locks=sum(p['held']for p in value['locks']),
            worker_log=value['worker_log'])
    else:
        result.update(state=value.get('batch/status.json'),exit=value.get('control/exit.json'),
            actual_runner=value.get('control/runner-process.json',{}).get('actual'),
            runs=[{'run_id':p['run_id'],'attempts':[{k:v for k,v in a.items()if k not in['terminal-manifest.json','result.json']}for a in p['attempts']]}for p in value['runs']],
            runner_log=value['runner_log'])
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',choices=['3090','4090'],required=True)
    main(parser.parse_args().host)
