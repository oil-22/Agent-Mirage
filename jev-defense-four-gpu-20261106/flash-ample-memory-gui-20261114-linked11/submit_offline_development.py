"""Submit at most once, only after actual29-GUI completion and model exits.

No polling, queue restart, service reuse, GPU preemption, browser reset or new
automation. A failure at any precondition leaves the experiment unsubmitted.
"""
import json
import time
from pathlib import Path

from control import HERE, R4090, remote, save, sha
from prepare_offline_development import PREP, PACKAGE, REMOTE, OUTPUT


def main():
    assert (PREP / 'stage-receipt.json').exists()
    assert not (PREP / 'submission.json').exists(), 'Inspect the existing submission; never resubmit'
    manifest = json.loads((PACKAGE / 'offline-manifest.json').read_bytes())
    expected = [v['run_id'] for v in json.loads((PACKAGE / 'native/plan.json').read_bytes())['queue']]
    code = 'ROOT=' + repr(R4090) + '\nEXPECTED=' + repr(expected) + '\nMANIFEST_SHA=' + repr(sha(PACKAGE / 'native/manifest.json')) + '\n' + r'''
import hashlib,json,os,time
from pathlib import Path
r=Path(ROOT);assert os.getuid()==1015
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
assert sha(r/'manifest.json')==MANIFEST_SHA
s=json.loads((r/'batch/status.json').read_bytes())
assert s['phase']=='completed'and s['expected']==s['completed']==s['processed']==29,'Current29 GUI must finish first'
exit_record=json.loads((r/'control/exit.json').read_bytes());assert exit_record['child_exit']==0
processes=[]
for name in ['process.json','runner-process.json']:
 row=json.loads((r/'control'/name).read_bytes());p=Path('/proc',str(row['pid']));actual=identity(row['pid'])if p.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==row[k]for k in ['uid','command','start_ticks'])
 assert not same,'Current GUI process has not exited';processes.append({'saved':row,'actual_if_pid_exists':actual,'same_live_process':same})
for name,h in json.loads((r/'control/postexit-seal.json').read_bytes()).items():assert sha(r/'control'/name)==h
rows=[]
for p in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):
 assert(p.parent/'seal.json').exists()
 t=json.loads(p.read_bytes());rows.append({'run_id':t['run']['run_id'],'folder':str(p.parent),'terminal_sha256':sha(p),'seal_sha256':sha(p.parent/'seal.json')})
assert len(rows)==29 and {v['run_id']for v in rows}==set(EXPECTED)
print(json.dumps({'time':time.time(),'terminals':rows,'GUI_child_exit':0,'actual_GUI_processes_exited':True,'GUI_processes':processes,'previous_manifest_sha256':MANIFEST_SHA,'batch_status':s,'new_model_GPU_GUI_calls':0}))
'''
    raw, op = remote('4090', code, 'offline-admission-actual29-GUI-exit-required')
    admission = json.loads(raw)
    operations = [str(op)]
    verified = []
    for start in range(0, 29, 5):
        selection = admission['terminals'][start:start + 5]
        code = 'ROWS=' + repr(selection) + '\n' + r'''
import hashlib,json
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
out=[]
for record in ROWS:
 p=Path(record['folder']);assert sha(p/'seal.json')==record['seal_sha256']and sha(p/'terminal.json')==record['terminal_sha256']
 for name,h in json.loads((p/'seal.json').read_bytes()).items():assert sha(p/name)==h
 t=json.loads((p/'terminal.json').read_bytes());assert t['run']['run_id']==record['run_id']and not t['infrastructure_failure']and not t['cleanup_error']
 previous='0'*64;count=0
 for line in(p/'controller/events.jsonl').read_text().splitlines():
  row=json.loads(line);h=row.pop('sha256');assert row['seq']==count and row['previous']==previous
  assert hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h
  previous=h;count+=1
 out.append({**record,'seal_verified':True,'chain_verified':True,'chain_head':previous,'events':count,'infrastructure_failure':False,'cleanup_error':None})
print(json.dumps(out))
'''
        raw, op = remote('4090', code, 'offline-admission-GUI-terminal-seals-' + str(start), timeout=55)
        verified.extend(json.loads(raw))
        operations.append(str(op))
    admission['terminals'] = verified
    admission['source_operations'] = operations
    evidence = PREP / ('post-GUI-admission-' + str(time.time_ns()))
    evidence.mkdir()
    save(evidence / 'admission.json', admission)
    save(evidence / 'seal.json', {'admission.json': sha(evidence / 'admission.json')})
    # Submission performs a fresh main exit/UUID/free-memory check. Empty
    # memory is not a lease; the launcher still acquires all locks itself.
    code = ('ROOT=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json'))
            + '\nADMISSION=' + repr(admission) + '\n' + r'''
import fcntl,json,os,sys,time
from pathlib import Path
p=Path(ROOT);sys.path.insert(0,str(p));import offline_guard as g
assert g.sha(p/'offline-manifest.json')==EXPECTED
m,plan=g.verify_package()
expected=[v['run_id']for v in g.load(p/'native/plan.json')['queue']]
g.validate_completion(g.load(g.PREVIOUS_OUT/'primary/status.json'),g.load(g.PREVIOUS_OUT/'primary/terminal.json'),g.load(g.PREVIOUS_OUT/'exit.json'),ADMISSION,expected)
processes=g.previous_models_exited()
lease=g.load(g.LEASE);holder=lease['holder'];actual=g.identity(holder['pid'])
assert actual['state']not in ['Z','X']and all(actual[k]==holder[k]for k in ['uid','command','start_ticks'])
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));assert os.readlink(proc/'fd'/str(row['fd']))==row['path']and 'WRITE '+str(holder['pid'])in(proc/'fdinfo'/str(row['fd'])).read_text()
previous=g.load(g.PREVIOUS_OUT/'expanded-lease.json');uuids={row['index']:row['uuid']for row in previous['gpu']}
g.validate_gpu(g.gpu_snapshot(),uuids)
assert not Path(m['output']).exists()
commands=g.LEASE.parent/'commands'
assert all(path.with_suffix('.claimed').exists()for path in commands.glob('*.json'))
admissionfile=p/'previous-GUI-admission.json';g.save(admissionfile,ADMISSION)
command=commands/'evidence-discipline-offline-development-20261114-01.json'
g.save(command,{'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'offline_launcher.py'),g.sha(admissionfile)],'script_sha256':g.sha(p/'offline_launcher.py')})
print(json.dumps({'command':str(command),'command_sha256':g.sha(command),'manifest_sha256':EXPECTED,'admission_sha256':g.sha(admissionfile),'previous_processes_actually_exited':processes,'once_only':True,'maximum_new_primary_calls':10,'new_GUI_Flash_scorer_calls':0,'time':time.time()}))
''')
    raw, op = remote('3090', code, 'submit-authorized-offline10-after-GUI-only-once')
    result = json.loads(raw)
    save(PREP / 'submission.json', {'result': result, 'operation': str(op), 'admission': str(evidence)})
    print(json.dumps(result))


if __name__ == '__main__':
    main()
