"""Inspect or submit only the new finite controls, after the live GUI is closed.

Submission never retries after an ambiguous observation. Inherited GPU leases
are acquired by the existing verified holder and launcher, never by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
GUI = HERE.parent / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

NAME = HERE.name
REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + NAME
OUTPUT = '/home/researcher/jev-defense-four-gpu-20261106/' + NAME
GUI3090 = '/home/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03'
GUI4090 = '/data/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03'

COMMON = r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
'''

def inspect():
    code = 'ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\n' + COMMON + r'''
r=Path(ROOT);package=Path(PACKAGE)
out={'time':time.time(),'remote_read_only':True,'new_model_GUI_calls':0,'output_exists':r.exists()}
out['manifest_sha256']=sha(package/'manifest.json')
out['claims']=[{'name':p.name,'sha256':sha(p),'value':json.loads(p.read_bytes())}for p in(package/'claims').glob('*.json')]
for name in ['launcher-process.json','worker-launch.json','worker/process.json','worker/status.json','worker/terminal.json','worker/failure.json','exit.json']:
 p=r/name
 if p.is_file():
  value=json.loads(p.read_bytes())
  if name.endswith('process.json'):value={'record':value,'actual':identity(value['pid'])}
  out[name]={'sha256':sha(p),'value':value}
events=r/'worker/journal/events.jsonl'
if events.is_file():
 previous='0'*64;counts={};n=0
 for line in events.read_bytes().splitlines():
  value=json.loads(line);sig=value.pop('sha256')
  assert value['seq']==n and value['previous']==previous and hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  previous=sig;n+=1;counts[value['kind']]=counts.get(value['kind'],0)+1
 out['journal']={'events':n,'head':previous,'counts':counts}
for name in ['worker.log','exit.json']:
 p=r/name
 if p.exists() and name.endswith('.log'):out['log']={'bytes':p.stat().st_size,'tail':p.read_bytes()[-2400:].decode(errors='replace')}
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'inspect-new-controls-08-only', timeout=55)
    print(json.dumps({'evidence': str(operation), 'snapshot': json.loads(output)}, ensure_ascii=False))

def submit(closed_audit):
    # A trusted, fully checked postexit audit is required, not a running flag.
    assert closed_audit is not None and closed_audit.is_file()
    gate = json.loads(closed_audit.read_bytes())
    assert gate['schema'] == 'closed-four-GUI-tracks-and-service-v1'
    assert gate['passed'] is True and gate['closed_tracks'] == 4
    assert gate['GUI_manifest_sha256'] == '584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67'
    assert gate['terminal_files_SHA_and_all_event_chains_verified'] is True
    assert gate['original_failures_and_requests_preserved'] is True
    assert not (HERE / 'submission-intent.json').exists()
    manifest = HERE / 'runtime-package/manifest.json'
    msha = sha(manifest)
    for name, expected in json.loads(manifest.read_bytes())['files'].items():
        assert sha(manifest.parent / name) == expected
    cpu = [p for p in HERE.glob('exact-request-CPU-admission-*/receipt.json')
           if json.loads(p.read_bytes()).get('passed') is True
           and json.loads(p.read_bytes()).get('manifest_sha256') == msha]
    assert len(cpu) == 1
    # Recheck remote GUI exit and exact original four terminal hashes immediately.
    code = 'ROOT=' + repr(GUI4090) + '\nEXPECTED=' + repr(gate['GUI_terminal_sha256']) + '\n' + COMMON + r'''
r=Path(ROOT);assert os.getuid()==1015
assert (r/'control/exit.json').is_file()
for name in ['control/runner-process.json','control/process.json']:
 p=r/name
 if p.is_file():
  record=json.loads(p.read_bytes());assert identity(record['pid']).get('absent') is True
assert len(EXPECTED)==4
for name,expected in EXPECTED.items():assert sha(r/name)==expected,name
print(json.dumps({'four_GUI_terminal_hashes_rechecked':True,'actual_runner_absent':True,'time':time.time()}))
'''
    _, gui_operation = remote('4090', code, 'admit-controls-08-after-closed-GUI', timeout=55)
    argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE_PACKAGE + '/launch_controls_once.py',
            '--manifest', REMOTE_PACKAGE + '/manifest.json', '--manifest-sha256', msha, '--output', OUTPUT]
    command = {'action': 'launch', 'argv': argv,
               'script_sha256': sha(manifest.parent / 'launch_controls_once.py')}
    save(HERE / 'submission-intent.json', {'time': time.time(), 'once_only': True,
        'manifest_sha256': msha, 'closed_audit': str(closed_audit), 'closed_audit_sha256': sha(closed_audit),
        'GUI_recheck_operation': str(gui_operation), 'ambiguous_observation_requires_inspection_not_resubmit': True})
    code = 'OUTPUT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nOLD=' + repr(GUI3090) + '\nCOMMAND=' + repr(command) + '\n' + COMMON + r'''
assert os.getuid()==1033
b=Path('/home/researcher/jev-defense-four-gpu-20261106');r=Path(OUTPUT);p=Path(PACKAGE)
assert not r.exists() and not any((p/'claims').glob('*.json'))
assert (Path(OLD)/'exit.json').is_file() and (Path(OLD)/'terminal-manifest.json').is_file()
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((Path(OLD)/name).read_bytes());assert identity(record['pid']).get('absent') is True
assert sha(p/'manifest.json')==COMMAND['argv'][5]
m=json.loads((p/'manifest.json').read_bytes())
for name,expected in m['files'].items():assert sha(p/name)==expected,name
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());h=lease['holder'];actual=identity(h['pid'])
assert all(str(actual[k])==str(h[k])for k in ['pid','uid','command','start_ticks']) and actual['state']not in ['Z','X']
for row in lease['lock_records']:
 proc=Path('/proc',str(h['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path'] and fd.stat().st_ino==row['inode'] and 'WRITE '+str(h['pid'])in info
target={x['uuid']for x in lease['gpu']};assert len(target)==4
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
cards={int(x.split(',')[0]):(x.split(',')[1].strip(),int(x.split(',')[2]))for x in gpu.splitlines()}
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid'] and cards[row['index']][1]>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(x.split(',')[0].strip()in target for x in compute.splitlines()if x.strip())
import fcntl
with Path(lease['inference_lock']).open('a')as mutex:
 fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
 # Only test mutex availability; actual worker independently acquires it after inherited-lock admission.
commands=b/'resource-attempt-20261106-01/commands'
assert all(x.with_suffix('.claimed').exists()for x in commands.glob('*.json'))
destination=commands/'source-bound-controls-20261109-08.json'
temporary=commands/('.new-controls08-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as f:f.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());f.flush();os.fsync(f.fileno())
os.link(temporary,destination);temporary.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(destination),'manifest_sha256':COMMAND['argv'][5],'time':time.time()}))
'''
    output, operation = remote('3090', code, 'submit-new-controls-08-once', timeout=55)
    save(HERE / 'submission.json', {'result': json.loads(output), 'evidence': str(operation),
                                    'manifest_sha256': msha})
    print(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inspect', 'submit'])
    parser.add_argument('--closed-audit', type=Path)
    args = parser.parse_args()
    if args.action == 'inspect':
        inspect()
    else:
        submit(args.closed_audit)
