"""Once-only new linked29 staging, owned-GPU launch, and native GUI launch."""
import argparse
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
PACKAGE = HERE / 'runtime-package-linked02'
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha

REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
OUTPUT = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
COMMON = r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
'''


def admitted():
    proof = json.loads((HERE / 'CPU-admission.json').read_bytes())
    assert proof['passed'] and proof['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    assert sha(proof['receipt']) == proof['receipt_sha256']
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    assert sha(PACKAGE / 'private.token') == manifest['auth_token_sha256']
    return manifest


def stage():
    admitted()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as stream:
        for p in PACKAGE.rglob('*'):
            if p.is_file():
                stream.writestr(p.relative_to(PACKAGE).as_posix(), p.read_bytes())
    prefix = 'PAYLOAD=' + repr(base64.b64encode(archive.getvalue()).decode()) + '\n'
    for host, target in [('3090', REMOTE_PACKAGE), ('4090', GUIROOT)]:
        # A successful first-host stage is never repeated if the second host
        # has a transient observation failure. Inspect the same target first.
        assert not (HERE / ('stage-' + host + '-intent.json')).exists()
        save(HERE / ('stage-' + host + '-intent.json'), {'time': time.time(), 'manifest_sha256': sha(PACKAGE / 'manifest.json')})
        code = 'ROOT=' + repr(target) + '\nMANIFEST_SHA=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + COMMON + r'''
import base64,io,zipfile
root=Path(ROOT);assert not root.exists();root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for item in archive.infolist():
  path=root/item.filename;assert path.resolve().is_relative_to(root.resolve())
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb')as stream:stream.write(archive.read(item))
(root/'private.token').chmod(0o600)
assert sha(root/'manifest.json')==MANIFEST_SHA
manifest=json.loads((root/'manifest.json').read_bytes())
for name,expected in manifest['files'].items():assert sha(root/name)==expected,name
assert sha(root/'private.token')==manifest['auth_token_sha256']
for path in root.rglob('*.py'):compile(path.read_text(),str(path),'exec')
if os.getuid()==1015:
 source=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/browser_env/actions.py').read_text()
 assert 'MOUSE_CLICK' in source and 'def create_mouse_click_action' in source
 state=json.loads((root/'carryover/state.json').read_bytes())
 for name,expected in state['native_source_SHA'].items():assert sha(name)==expected,name
 assert sha(state['original_trace'])==state['original_trace_sha256']
 assert sha(state['original_private_trajectory'])==state['original_private_trajectory_sha256']
 old=root.parent/'full-history-gui-development-20261109-23/environment-preflight/receipt.json'
 assert sha(old)==sha(root/'environment-preflight/receipt.json')
available=int(next(row.split()[1]for row in Path('/proc/meminfo').read_text().splitlines()if row.startswith('MemAvailable:')))*1024
assert os.getuid()!=1033 or available>=64*1024**3
print(json.dumps({'root':str(root),'uid':os.getuid(),'manifest_sha256':MANIFEST_SHA,'files_verified':len(manifest['files']),'RAM_available_bytes':available,'model_GUI_scorer_calls':0}))
'''
        output, operation = remote(host, code, 'stage-linked29-' + host + '-once', timeout=55, private_prefix=prefix)
        save(HERE / ('stage-' + host + '.json'), {'result': json.loads(output), 'operation': str(operation)})
        print(output)


def service():
    admitted()
    assert all((HERE / ('stage-' + host + '.json')).is_file() for host in ['3090', '4090'])
    assert not (HERE / 'service-submission-intent.json').exists()
    msha = sha(PACKAGE / 'manifest.json')
    argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE_PACKAGE + '/launch_gui_service_once.py',
            '--manifest', REMOTE_PACKAGE + '/manifest.json', '--manifest-sha256', msha, '--output', OUTPUT]
    command = {'action': 'launch', 'argv': argv, 'script_sha256': sha(PACKAGE / 'launch_gui_service_once.py')}
    save(HERE / 'service-submission-intent.json', {'time': time.time(), 'manifest_sha256': msha,
        'carried_original_track_counts': {'actor': 11, 'judge': 34, 'evidence': 0},
        'no_duplicate_after_observation_timeout': True, 'once_only': True})
    code = 'PACKAGE=' + repr(REMOTE_PACKAGE) + '\nOUTPUT=' + repr(OUTPUT) + '\nCOMMAND=' + repr(command) + '\n' + COMMON + r'''
import fcntl,socket
base=Path('/home/researcher/jev-defense-four-gpu-20261106');package=Path(PACKAGE)
assert os.getuid()==1033 and not Path(OUTPUT).exists()and not any((package/'claims').glob('*.json'))
manifest=json.loads((package/'manifest.json').read_bytes());assert sha(package/'manifest.json')==COMMAND['argv'][5]
for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
for oldname,expected_exit in [('full-history-gui-development-20261109-23',1),('memory-scheduled-capacity-20261109-26',0)]:
 old=base/oldname
 assert (old/'terminal-manifest.json').is_file()
 assert json.loads((old/'exit.json').read_bytes())['worker_exit_code']==expected_exit
 for name in ['launcher-process.json','worker/process.json']:
  record=json.loads((old/name).read_bytes());assert identity(record['pid']).get('absent')is True
leasepath=base/'resource-attempt-20261106-01/lease.json';lease=json.loads(leasepath.read_bytes())
assert sha(leasepath)==manifest['lease_sha256']
holder=lease['holder'];actual=identity(holder['pid'])
assert all(str(actual[k])==str(holder[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9 and {row['index']for row in lease['gpu']}=={4,5,6,7}
cards={}
for row in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
 index,uuid,free=[value.strip()for value in row.split(',')];cards[int(index)]=(uuid,int(free))
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
targets={row['uuid']for row in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(row.split(',')[0].strip()in targets for row in compute.splitlines()if row.strip())
with Path(lease['inference_lock']).open('a')as mutex:fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
with socket.socket()as connection:connection.bind(('192.0.2.11',19139))
commands=base/'resource-attempt-20261106-01/commands'
assert all(path.with_suffix('.claimed').exists()for path in commands.glob('*.json'))
destination=commands/'memory-scheduled-full-history-gui-20261109-29.json';temporary=commands/('.new29-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as stream:stream.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());stream.flush();os.fsync(stream.fileno())
os.link(temporary,destination);temporary.unlink()
print(json.dumps({'submitted_once':True,'command':str(destination),'holder':actual,'held_resource_locks':9,'physical_GPUs':list(range(4,8)),'minimum_free_MiB':min(cards[i][1]for i in range(4,8)),'manifest_sha256':sha(package/'manifest.json'),'prior23and26workers_absent':True}))
'''
    output, operation = remote('3090', code, 'submit-new-linked29-service-once', timeout=55)
    save(HERE / 'service-submission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def gui():
    admitted()
    assert (HERE / 'service-submission.json').is_file() and not (HERE / 'GUI-submission-intent.json').exists()
    msha = sha(PACKAGE / 'manifest.json')
    save(HERE / 'GUI-submission-intent.json', {'time': time.time(), 'manifest_sha256': msha,
        'once_only': True, 'no_duplicate_after_observation_timeout': True})
    code = 'ROOT=' + repr(GUIROOT) + '\nMSHA=' + repr(msha) + '\n' + COMMON + r'''
import fcntl
root=Path(ROOT);assert os.getuid()==1015 and sha(root/'manifest.json')==MSHA
assert not (root/'control').exists()and not(root/'batch').exists()and not(root/'background').exists()
manifest=json.loads((root/'manifest.json').read_bytes())
for name,expected in manifest['files'].items():assert sha(root/name)==expected,name
old=root.parent/'full-history-gui-development-20261109-23'
for name in ['control/runner-process.json','control/process.json']:
 record=json.loads((old/name).read_bytes());assert identity(record['pid']).get('absent')is True
with (root.parent/'.full-gui-site29980.lock').open('a')as mutex:fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
assert all(row['Id']==expected and row['Config']['Labels']['owner']=='whz-qwen27-vwa'and row['State']['Running']for row,expected in zip(rows,ids))
assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(row.get('Name')=='qwen27_vwa_db_data'for row in rows[1]['Mounts'])
claim=root/'background';claim.mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(root/'gui_outer.py'),'--manifest-sha256',MSHA]
with (claim/'outer.log').open('xb')as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
actual=identity(child.pid);assert actual['uid']==1015 and actual['command']==' '.join(argv)
(claim/'launch.json').write_text(json.dumps({'identity':actual,'argv':argv,'manifest_sha256':MSHA,'once_only':True,'time':time.time()},indent=2))
print(json.dumps({'submitted_once':True,'identity':actual,'root':str(root),'manifest_sha256':MSHA,'native_live_restore_required_before_action11':True,'model_calls_from_submission':0}))
'''
    output, operation = remote('4090', code, 'submit-new-linked29-GUI-once', timeout=55,
        interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    save(HERE / 'GUI-submission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def inspect():
    code = 'ROOT=' + repr(OUTPUT) + '\n' + COMMON + r'''
root=Path(ROOT);out={'time':time.time(),'root_exists':root.exists(),'new_inference_requests':0}
for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/terminal.json','worker/failure.json','worker/ready.json','exit.json']:
 path=root/name
 if path.is_file():
  value=json.loads(path.read_bytes());out[name]={'record':value,'actual':identity(value['pid'])}if name.endswith('process.json')else value
if (root/'worker.log').is_file():out['log_tail']=(root/'worker.log').read_bytes()[-1600:].decode(errors='replace')
out['request_count']=len(list((root/'worker/requests').glob('*')))
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'inspect-same-new29-actual-handles-no-inference', timeout=55)
    print(json.dumps({'evidence': str(operation), 'snapshot': json.loads(output)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['stage', 'service', 'gui', 'inspect'])
    {'stage': stage, 'service': service, 'gui': gui, 'inspect': inspect}[parser.parse_args().action]()
