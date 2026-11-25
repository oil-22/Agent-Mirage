"""Once-only approved remaining29 deployment; preserve all three old endpoints."""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PACKAGE = HERE / 'runtime-package'
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
OLD_OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33'
OLD_GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33'
COMMON = r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
def sha(path):
 value=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024*1024),b''):value.update(part)
 return value.hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
def same_live(record):
 actual=identity(record['pid'])
 return not actual.get('absent')and all(str(actual[k])==str(record[k])for k in['pid','uid','command','start_ticks'])and actual['state']not in['Z','X']
def verify_package(root,expected):
 assert sha(root/'manifest.json')==expected
 m=json.loads((root/'manifest.json').read_bytes())
 for name,value in m['files'].items():assert sha(root/name)==value,name
 assert sha(root/'private.token')==m['auth_token_sha256']
 sys.path.insert(0,str(root))
 from source_decision_gate import require_finalized
 require_finalized(root/'gpu_server.py')
 assert m['tracks']==29 and m['total_original_tracks']==32
 return m
'''


def admitted():
    proof = json.loads((HERE / 'CPU-admission.json').read_bytes())
    assert proof['passed'] and proof['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    m = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, digest in m['files'].items():
        assert sha(PACKAGE / name) == digest, name
    assert m['tracks'] == 29 and m['total_original_tracks'] == 32
    assert m['initial_transport_counts_for_all_remaining_tracks'] == dict(actor=0, judge=0, evidence=0)
    assert sha(PACKAGE / 'private.token') == m['auth_token_sha256']
    assert m['human_decision_receipt_sha256'] == sha(HERE / 'human-source-condition-decision.json')
    decision = json.loads((HERE / 'human-source-condition-decision.json').read_bytes())
    assert decision['choice'] == 'adopt_exact_decoded_native_STOP_answer_source'
    assert m['authorized_finite_joint_development'] and m['source_condition_decision_received']
    return m


def stage():
    m = admitted()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in list(m['files']) + ['manifest.json', 'private.token']:
            archive.writestr(name, (PACKAGE / name).read_bytes())
    private_prefix = 'PAYLOAD=' + repr(base64.b64encode(buffer.getvalue()).decode()) + '\n'
    for host, target in [('3090', REMOTE_PACKAGE), ('4090', GUIROOT)]:
        intent = HERE / ('stage-' + host + '-intent.json')
        assert not intent.exists(), 'Inspect this exact target after observation failure; never duplicate stage'
        save(intent, dict(time=time.time(), manifest_sha256=sha(PACKAGE / 'manifest.json'), once_only=True))
        code = 'ROOT=' + repr(target) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + COMMON + r'''
import base64,io,zipfile
root=Path(ROOT);assert not root.exists()and not root.is_symlink()
assert root.parent.is_dir()and root.parent.stat().st_uid==os.getuid()
root.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for item in archive.infolist():
  target=root/item.filename;assert target.resolve().is_relative_to(root.resolve())
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb')as stream:stream.write(archive.read(item))
(root/'private.token').chmod(0o600)
m=verify_package(root,EXPECTED)
for path in root.rglob('*.py'):compile(path.read_text(),str(path),'exec')
assert m['decision_adapter_loaded']is False and m['actual_auxiliary']=='Qwen/Qwen3.5-9B'
assert sha(root/'plan.json')=='51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
closed=[]
if os.getuid()==1015:
 base=root.parent
 for row in json.loads((root/'continuation.json').read_bytes())['terminal_copies']:
  old=base/('prefill-scheduled-full-history-gui-20261109-32'if row['run_id']=='fullhistory23-T000-clean-noaux'else'remaining-full-history-gui-20261110-33')
  attempts=list((old/'batch/runs'/row['run_id']).glob('attempt-*'));assert len(attempts)==1
  terminal=next(p for p in[attempts[0]/'complete.json',attempts[0]/'technical-failure.json']if p.is_file())
  assert sha(terminal)==row['sha256'];closed.append({'run_id':row['run_id'],'terminal_sha256':row['sha256']})
 for dirname in['prefill-scheduled-full-history-gui-20261109-32','remaining-full-history-gui-20261110-33']:
  old=base/dirname
  for name in['control/process.json','control/runner-process.json']:
   record=json.loads((old/name).read_bytes());assert not same_live(record)
 for row in json.loads((root/'native-bindings-public.json').read_bytes())['tasks']:
  assert sha(row['original_private_path'])==row['original_private_SHA']
print(json.dumps({'root':str(root),'uid':os.getuid(),'files_verified':len(m['files']),'manifest_sha256':EXPECTED,
 'three_original_GUI_terminal_SHAs_bound':closed,'human_selected_source_mapping':True,'new_model_GUI_scorer_calls':0},ensure_ascii=True))
'''
        output, operation = remote(host, code, 'stage-approved-remaining29-once-' + host,
                                   timeout=55, private_prefix=private_prefix)
        save(HERE / ('stage-' + host + '.json'), dict(result=json.loads(output), operation=str(operation)))
        print(output)


def service():
    admitted()
    assert all((HERE / ('stage-' + host + '.json')).exists() for host in ['3090', '4090'])
    assert not (HERE / 'service-submission-intent.json').exists(), 'Inspect prior submission; no duplicate launch'
    expected = sha(PACKAGE / 'manifest.json')
    argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE_PACKAGE + '/launch_gui_service_once.py',
            '--manifest', REMOTE_PACKAGE + '/manifest.json', '--manifest-sha256', expected, '--output', OUTPUT]
    command = dict(action='launch', argv=argv, script_sha256=sha(PACKAGE / 'launch_gui_service_once.py'))
    save(HERE / 'service-submission-intent.json', dict(time=time.time(), manifest_sha256=expected,
         first_run='fullhistory23-T000-stale_replace-noaux', initial_counts=dict(actor=0, judge=0, evidence=0), once_only=True))
    code = ('PACKAGE=' + repr(REMOTE_PACKAGE) + '\nOUTPUT=' + repr(OUTPUT) + '\nOLD=' + repr(OLD_OUTPUT)
            + '\nEXPECTED=' + repr(expected) + '\nCOMMAND=' + repr(command) + '\n' + COMMON + r'''
import fcntl,socket
base=Path('/home/researcher/jev-defense-four-gpu-20261106');package=Path(PACKAGE);old=Path(OLD)
assert os.getuid()==1033 and not Path(OUTPUT).exists()and not any((package/'claims').glob('*.json'))
m=verify_package(package,EXPECTED)
assert sha(old/'manifest.json')=='e64fc8e42a144cd1cc426942093a6edaf51204fba13918286c41e51f8d7b15ef'
assert(old/'exit.json').is_file()and(old/'worker/terminal.json').is_file()and(old/'terminal-manifest.json').is_file()
for name in['launcher-process.json','worker/process.json']:
 record=json.loads((old/name).read_bytes());assert not same_live(record)
leasepath=base/'resource-attempt-20261106-01/lease.json';lease=json.loads(leasepath.read_bytes())
assert sha(leasepath)==m['lease_sha256']
holder=lease['holder'];actual=identity(holder['pid'])
assert same_live(holder)and all(str(actual[k])==str(m['expected_holder'][k])for k in['pid','uid','command','start_ticks'])
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9 and{row['index']for row in lease['gpu']}=={4,5,6,7}
cards={}
for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
 index,uuid,free=[v.strip()for v in line.split(',')];cards[int(index)]=(uuid,int(free))
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
targets={row['uuid']for row in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(line.split(',')[0].strip()in targets for line in compute.splitlines()if line.strip())
with Path(lease['inference_lock']).open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
with socket.socket()as check:check.bind(('192.0.2.11',19142))
ram=int(next(line.split()[1]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')))*1024
assert ram>=64*1024**3
storage=Path(OUTPUT).parent
assert storage.resolve()==storage and not storage.is_symlink()and storage.stat().st_uid==1033
assert not Path(OUTPUT).exists();v=os.statvfs(storage);available=v.f_bavail*v.f_frsize
assert available>=1024**4 and storage.stat().st_dev!=Path('/home/researcher').stat().st_dev
commands=base/'resource-attempt-20261106-01/commands'
assert all(path.with_suffix('.claimed').exists()for path in commands.glob('*.json'))
destination=commands/'remaining29-full-history-gui-20261110-37.json'
temporary=commands/('.remaining29-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as stream:stream.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());stream.flush();os.fsync(stream.fileno())
os.link(temporary,destination);temporary.unlink()
print(json.dumps({'submitted_once':True,'command':str(destination),'holder':actual,'held_locks':9,'physical_GPUs':[4,5,6,7],
 'minimum_free_MiB':min(cards[i][1]for i in[4,5,6,7]),'available_RAM_bytes':ram,'storage_free_bytes':available,
 'all29_future_full_history_fit_not_proven':True,'originals_deleted_moved_or_compressed':False,'manifest_sha256':EXPECTED,
 'new_model_GUI_calls_from_submission':0},ensure_ascii=True))
''')
    output, operation = remote('3090', code, 'submit-approved-remaining29-owned-lock-launch-once', timeout=55)
    save(HERE / 'service-submission.json', dict(result=json.loads(output), operation=str(operation)))
    print(output)


def gui():
    admitted()
    assert (HERE / 'service-submission.json').is_file() and not (HERE / 'GUI-submission-intent.json').exists()
    expected = sha(PACKAGE / 'manifest.json')
    save(HERE / 'GUI-submission-intent.json', dict(time=time.time(), manifest_sha256=expected, once_only=True))
    code = ('ROOT=' + repr(GUIROOT) + '\nOLD=' + repr(OLD_GUIROOT) + '\nEXPECTED=' + repr(expected) + '\n' + COMMON + r'''
import fcntl,requests
root=Path(ROOT);old=Path(OLD);assert os.getuid()==1015;m=verify_package(root,EXPECTED)
assert not(root/'control').exists()and not(root/'batch').exists()and not(root/'background').exists()
for name in['control/runner-process.json','control/process.json']:
 record=json.loads((old/name).read_bytes());assert not same_live(record)
assert(old/'control/exit.json').is_file()
token=root/'private.token';assert token.stat().st_mode&0o077==0
response=requests.get(m['model_url'],headers={'Authorization':'Bearer '+token.read_text().strip()},timeout=20);response.raise_for_status()
health=response.json();assert health['phase']=='ready_gui'and health['manifest_sha256']==EXPECTED and health['actual_prior_model_attempts']==0
with(root.parent/'.full-gui-site29980.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
assert all(row['Id']==expected and row['Config']['Labels']['owner']=='whz-qwen27-vwa'and row['State']['Running']for row,expected in zip(rows,ids))
assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(row.get('Name')=='qwen27_vwa_db_data'for row in rows[1]['Mounts'])
claim=root/'background';claim.mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(root/'gui_outer.py'),'--manifest-sha256',EXPECTED]
with(claim/'outer.log').open('xb')as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=str(root),
  env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
actual=identity(child.pid);assert actual['uid']==1015 and actual['command']==' '.join(argv)
(claim/'launch.json').write_text(json.dumps({'identity':actual,'argv':argv,'manifest_sha256':EXPECTED,'once_only':True,'time':time.time()},indent=2))
print(json.dumps({'submitted_once':True,'identity':actual,'root':str(root),'manifest_sha256':EXPECTED,
 'first_run':'fullhistory23-T000-stale_replace-noaux','all_remaining_initial_counts':{'actor':0,'judge':0,'evidence':0},
 'original_terminal_track_rerun':False,'new_model_calls_from_submission':0},ensure_ascii=True))
''')
    output, operation = remote('4090', code, 'submit-approved-remaining29-native-GUI-once', timeout=55,
                               interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    save(HERE / 'GUI-submission.json', dict(result=json.loads(output), operation=str(operation)))
    print(output)


def inspect(baseline=None):
    admitted()
    prior = {}
    if baseline is not None:
        baseline = Path(baseline).resolve()
        assert baseline.parent == HERE and baseline.name.startswith('actual-evidence-')
        for name, expected in json.loads((baseline / 'seal.json').read_bytes()).items():
            assert sha(baseline / name) == expected
        previous = json.loads((baseline / '3090.json').read_bytes())
        assert previous['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
        for row in previous['sealed_requests']:
            authority = row.get('full_SHA_verification_authority', dict(evidence=str(baseline),
                request=row['request'], request_seal_sha256=row['seal_sha256']))
            origin = Path(authority['evidence'])
            assert origin.parent == HERE
            for name, expected in json.loads((origin / 'seal.json').read_bytes()).items():
                assert sha(origin / name) == expected
            original = next(value for value in json.loads((origin / '3090.json').read_bytes())['sealed_requests']
                            if value['request'] == row['request'])
            assert original['files_verified'] > 0 and original['seal_sha256'] == authority['request_seal_sha256'] == row['seal_sha256']
            prior[row['request']] = dict(seal_sha256=row['seal_sha256'], full_SHA_verification_authority=authority)
    target = HERE / ('actual-evidence-' + str(time.time_ns()))
    target.mkdir()
    code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json'))
            + '\nPRIOR=' + repr(prior) + '\n' + COMMON + r'''
r=Path(ROOT);package=Path(PACKAGE);m=verify_package(package,EXPECTED)
lease=json.loads(Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json').read_bytes())
h=lease['holder'];actual=identity(h['pid'])
assert all(str(actual[k])==str(h[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
locks=[]
for row in lease['lock_records']:
 proc=Path('/proc',str(h['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(h['pid'])in info
 locks.append(row['path'])
out={'time':time.time(),'root_exists':r.exists(),'manifest_sha256':EXPECTED,'actual_holder':actual,'held_locks':locks,'remote_read_only':True,'new_model_GUI_calls':0}
for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/ready.json','worker/terminal.json','worker/failure.json','exit.json']:
 p=r/name
 if p.is_file():
  value=json.loads(p.read_bytes());out[name]={'sha256':sha(p),'value':value,'actual':identity(value['pid'])}if name.endswith('process.json')else {'sha256':sha(p),'value':value}
if(r/'worker/loaded.json').is_file():
 value=json.loads((r/'worker/loaded.json').read_bytes())
 out['worker/loaded.json']={'sha256':sha(r/'worker/loaded.json'),'value':{k:v for k,v in value.items()if k!='actual_cuda_tensors'}}
out['sealed_requests']=[]
for p in sorted((r/'worker/requests').glob('*')):
 if not(p/'seal.json').is_file():continue
 seal=json.loads((p/'seal.json').read_bytes())
 old=PRIOR.get(p.name)
 if old is not None:assert sha(p/'seal.json')==old['seal_sha256']
 else:
  for name,value in seal.items():assert sha(p/name)==value,name
 wire=json.loads((p/'external-wire.json').read_bytes());payload=wire['payload']
 op='evidence'if'image_base64'in payload else payload['operation']
 item={'request':p.name,'seal_sha256':sha(p/'seal.json'),'files_verified':len(seal),'operation':op,
  'trajectory_id':wire['trajectory_id'],'decision_index':wire['decision_index'],'attempt_index':wire['attempt_index'],
  'all_original_binary_files_newly_full_SHA_verified_this_poll':old is None}
 if old is not None:item['full_SHA_verification_authority']=old['full_SHA_verification_authority']
 out['sealed_requests'].append(item)
assert set(PRIOR)<={row['request']for row in out['sealed_requests']},'Previously sealed reply disappeared'
def chain(path):
 raw=path.read_bytes();raw=raw[:raw.rfind(b'\n')+1]if raw and not raw.endswith(b'\n')else raw
 previous='0'*64;counts={};n=0
 for line in raw.splitlines():
  event=json.loads(line);signature=event.pop('sha256')
  assert event['seq']==n and event['previous']==previous and hashlib.sha256(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
  previous=signature;counts[event['kind']]=counts.get(event['kind'],0)+1;n+=1
 return {'events':n,'head':previous,'counts':counts}
if(r/'worker/journal/events.jsonl').is_file():out['journal']=chain(r/'worker/journal/events.jsonl')
out['GPU']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
worker=out.get('worker/process.json',{}).get('actual',{});worker_pid=worker.get('pid')
uuids={row['uuid']for row in lease['gpu']}
for line in out['compute'].splitlines():
 uuid,pid,memory=[v.strip()for v in line.split(',')]
 if uuid in uuids:
  assert int(pid)==worker_pid and worker.get('uid')==1033
  assert worker['command'].startswith('/opt/whz/conda-envs/webmall-vlm/bin/python -u '+PACKAGE+'/gpu_server.py ')
out['log_tail']=(r/'worker.log').read_bytes()[-1200:].decode(errors='replace')if(r/'worker.log').exists()else None
if r.parent.exists():
 v=os.statvfs(r.parent);out['service_storage_free_bytes']=v.f_bavail*v.f_frsize
print(json.dumps(out))
''')
    output, operation = remote('3090', code, 'inspect-same-remaining31-UID-command-nine-locks-sealed-replies', timeout=55)
    service_value = json.loads(output)
    save(target / '3090.json', service_value)
    save(target / '3090-operation.json', dict(operation=str(operation)))
    code = ('ROOT=' + repr(GUIROOT) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + COMMON + r'''
root=Path(ROOT);verify_package(root,EXPECTED)
out={'time':time.time(),'read_only':True,'new_model_GUI_calls':0,'manifest_sha256':EXPECTED}
for name in ['background/launch.json','control/process.json','control/runner-process.json','control/exit.json','batch/status.json','batch/uncaught-failure.json']:
 p=root/name
 if p.is_file():
  value=json.loads(p.read_bytes());record=value.get('identity',value)
  out[name]={'sha256':sha(p),'value':value}
  if'pid'in record:out[name]['actual']=identity(record['pid'])
out['GUI_event_chains']=[]
for path in sorted((root/'batch/runs').glob('*/attempt-*/events.jsonl')):
 raw=path.read_bytes();raw=raw[:raw.rfind(b'\n')+1]if raw and not raw.endswith(b'\n')else raw
 previous='0'*64;counts={};n=0
 for line in raw.splitlines():
  event=json.loads(line);signature=event.pop('sha256')
  assert event['seq']==n and event['previous']==previous and hashlib.sha256(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
  previous=signature;counts[event['kind']]=counts.get(event['kind'],0)+1;n+=1
 out['GUI_event_chains'].append({'path':str(path),'events':n,'head':previous,'counts':counts})
out['runner_log_tail']=(root/'control/runner.log').read_bytes()[-1200:].decode(errors='replace')if(root/'control/runner.log').exists()else None
print(json.dumps(out))
''')
    output, operation = remote('4090', code, 'inspect-same-remaining31-native-GUI-identity-chain-no-checker-text', timeout=55)
    gui_value = json.loads(output)
    save(target / '4090.json', gui_value)
    save(target / '4090-operation.json', dict(operation=str(operation)))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    print(json.dumps(dict(evidence=str(target), manifest_sha256=sha(PACKAGE / 'manifest.json'),
        actual_worker=service_value.get('worker/process.json'), service_state=service_value.get('worker/status.json'),
        service_terminal=service_value.get('worker/terminal.json'), held_locks=len(service_value['held_locks']),
        sealed_requests=service_value['sealed_requests'], GUI_state=gui_value.get('batch/status.json'),
        GUI_runner=gui_value.get('control/runner-process.json'), service_storage_free_bytes=service_value.get('service_storage_free_bytes'),
        new_model_GUI_calls=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['stage', 'service', 'gui', 'inspect'])
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    assert args.action == 'inspect' or args.baseline is None
    inspect(args.baseline) if args.action == 'inspect' else globals()[args.action]()
