"""Recorded one-time upload/launch and read-only monitoring of the new offline job."""
import base64
import io
import json
import sys
import time
import zipfile
from pathlib import Path

from remote_util import HERE, remote, save, sha


def prepared():
    pointer = json.loads((HERE / 'preparation-current.json').read_bytes())
    package = Path(pointer['package']); manifest = json.loads((package / 'manifest.json').read_bytes())
    assert sha(package / 'manifest.json') == pointer['manifest_sha256']
    for name, expected in manifest['files'].items():
        assert sha(package / name) == expected, name
    return pointer, package, manifest


def inspect():
    _, _, m = prepared()
    code = (HERE / 'resource_guard.py').read_text('utf8') + '\n'
    code += '''
import time
out=Path(OUTPUT);parent=out.parent
data={'time':time.time(),'actual_UID':os.getuid(),'GPU':gpu_snapshot(),'output_exists':out.exists(),'submitted':(parent/'submit-once.json').exists()}
for name in ['launcher-process.json','worker-launch.json','service/process.json','service/terminal.json','exit.json','released.json']:
 if(out/name).exists():data[name]=json.loads((out/name).read_bytes())
for name in ['launcher-process.json','service/process.json']:
 if name in data:
  saved=data[name];proc=Path('/proc',str(saved['pid']))
  actual=identity(saved['pid'])if proc.exists()else None
  data[name+'-actual']=actual
  if actual and all(actual[k]==saved[k]for k in['uid','command','start_ticks']):
   data[name+'-locks']={p.name:(Path('/proc',str(saved['pid']),'fdinfo',p.name).read_text())for p in(Path('/proc',str(saved['pid']),'fd')).iterdir()if 'lock:' in Path('/proc',str(saved['pid']),'fdinfo',p.name).read_text()}
data['postexit_seal_exists']=(out/'postexit-seal.json').exists()
for name in ['worker.log']:
 if(out/name).exists():
  raw=(out/name).read_bytes();data[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'tail':raw[-2200:].decode(errors='replace')}
if(out/'service/requests').exists():
 data['actual_complete_responses']=sum((p/'response.json').exists()for p in(out/'service/requests').iterdir())
print(json.dumps(data))
'''
    raw, operation = remote('3090', 'OUTPUT=' + repr(m['output']) + '\n' + code, 'offline-read-only-actual-ownership-and-progress')
    root = HERE / ('inspection-' + str(time.time_ns())); root.mkdir()
    result = json.loads(raw)
    save(root / 'result.json', {'operation': str(operation), **result})
    save(root / 'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    print(json.dumps({'root': str(root), **result}))


def stage():
    pointer, package, m = prepared()
    assert not (HERE / 'staging-receipt.json').exists()
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        for q in package.rglob('*'):
            if q.is_file(): archive.write(q, q.relative_to(package).as_posix())
    code = '''
import base64,hashlib,io,json,zipfile
from pathlib import Path
root=Path(REMOTE);root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(BLOB,validate=True)))as archive:
 for name in archive.namelist():
  p=root/name;assert p.resolve().is_relative_to(root.resolve());p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(archive.read(name))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'manifest.json')==MANIFEST
m=json.loads((root/'manifest.json').read_bytes())
assert {p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()}==set(m['files'])|{'manifest.json'}
for name,h in m['files'].items():assert sha(root/name)==h,name
print(json.dumps({'root':str(root),'manifest_sha256':MANIFEST,'files':len(m['files']),'new_model_GUI_calls':0}))
'''
    raw, operation = remote('3090', 'REMOTE=' + repr(m['remote_package']) + '\nMANIFEST=' + repr(pointer['manifest_sha256']) + '\nBLOB=' + repr(base64.b64encode(data.getvalue()).decode()) + '\n' + code, 'stage-frozen-approved-offline-package', timeout=90)
    save(HERE / 'staging-receipt.json', {'operation': str(operation), 'result': json.loads(raw)})
    print(raw)


def submit():
    pointer, _, m = prepared()
    assert (HERE / 'staging-receipt.json').exists() and not (HERE / 'submission-receipt.json').exists()
    code = '''
import json,os,subprocess,sys,time
from pathlib import Path
p=Path(P);o=Path(O)
sys.path.insert(0,str(p/'flash'))
from resource_guard import sha,gpu_snapshot,identity,check_card
assert os.getuid()==1033 and sha(p/'manifest.json')==MANIFEST
m=json.loads((p/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(p/name)==h,name
assert not o.exists(),'Never launch a completed or previously attempted root'
config=json.loads((p/'flash/service-config.json').read_bytes());snap=gpu_snapshot();i=config['physical_gpu']
check_card(snap,i,snap['gpu'][i]['uuid'],False,os.getpid())
o.parent.mkdir(parents=True,exist_ok=True)
claim=o.parent/'submit-once.json'
with claim.open('x',encoding='utf8')as f:json.dump({'time':time.time(),'manifest_sha256':MANIFEST,'max_calls':20,'new_GUI_authorized':False},f)
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(p/'run_offline.py')]
with(o.parent/'launcher.log').open('xb')as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
value={'time':time.time(),'identity':identity(child.pid),'argv':argv,'manifest_sha256':MANIFEST,'new_primary_GUI_paid_calls':0}
with(o.parent/'submission.json').open('x',encoding='utf8')as f:json.dump(value,f,indent=2)
print(json.dumps(value))
'''
    raw, operation = remote('3090', 'P=' + repr(m['remote_package']) + '\nO=' + repr(m['output']) + '\nMANIFEST=' + repr(pointer['manifest_sha256']) + '\n' + code, 'submit-once-twenty-Flash-only-calls')
    save(HERE / 'submission-receipt.json', {'operation': str(operation), 'result': json.loads(raw)})
    print(raw)


if __name__ == '__main__':
    {'inspect': inspect, 'stage': stage, 'submit': submit}[sys.argv[1]]()
