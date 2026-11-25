"""Read-only public metadata collection; never model health/POST or private files."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
code=r'''import base64,hashlib,json
from pathlib import Path
base=Path('/data/researcher/jev-defense-four-gpu-20261106')
selected={
'native-env-retry-preflight-01':['receipt.json','seal.json','native-env-dependency-inventory.json'],
'gui-final-readiness-retry01':['auxiliary-config.json','preparation.json','readiness.json','launch-spec.json','seal.json'],
'ownership-transport-proof-1793979817792141700':['ownership-transport-proof.json','4090-authenticated-health.json',
    'wrapper-source-binding.json','bridge-inspect.json','bridge-process-identity.json','3090-ownership-inspection.json'],
'gui-outer-background-retry01':['actualprocess.json','once-only-launch.json'],
'gui-outer-control-retry01':['fresh-health.json','runner-process.json','wrapper-process.json','exact-command.json',
    'native-environment.json','finalization.json','postexit-sha256.json','batch-postexit-sha256.json'],
'gui-once-wrapper-retry01':['source-seal.json','cpu-receipt.json']}
result={};missing=[]
for folder,names in selected.items():
    for name in names:
        path=base/folder/name
        assert 'PRIVATE'not in name and'token'not in name.lower()
        if not path.exists():missing.append(folder+'/'+name);continue
        assert path.is_file()and not path.is_symlink()
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        assert raw==path.read_bytes(),'Expected immutable public source changed during read'
        result[folder+'/'+name]={'sha256':digest,'data':base64.b64encode(raw).decode()}
print(json.dumps({'public_files':result,'not_yet_present':missing,'new_model_GUI_or_health_requests':0}))
'''
run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=90)
out=ROOT/('gui-retry-public-evidence-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stderr.txt').write_text(run.stderr,encoding='utf8')
if run.returncode:
    (out/'failure.stdout.txt').write_text(run.stdout,encoding='utf8');raise SystemExit(run.returncode)
data=json.loads(run.stdout)
for name,item in data['public_files'].items():
    target=out/name;assert target.resolve().is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];target.write_bytes(raw)
assert hashlib.sha256((out/'gui-final-readiness-retry01/launch-spec.json').read_bytes()).hexdigest()=='eda082227b74ddc005c1c7a2ffe0cfd8608bdac928817aa5a6b08a0a543d7dd8'
for group in('native-env-retry-preflight-01','gui-final-readiness-retry01'):
    root=out/group
    for name,digest in json.loads((root/'seal.json').read_bytes()).items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
proof=json.loads((out/'ownership-transport-proof-1793979817792141700/ownership-transport-proof.json').read_bytes())
prefix='/data/researcher/jev-defense-four-gpu-20261106/'
for item in proof['source_evidence']:
    local=out/item['path'].removeprefix(prefix)
    assert hashlib.sha256(local.read_bytes()).hexdigest()==item['sha256']
receipt={'local':str(out),'files_verified':len(data['public_files']),
    'source_sha256':{name:item['sha256']for name,item in data['public_files'].items()},
    'not_yet_present':data['not_yet_present'],'new_model_GUI_or_health_requests':0,
    'native_env_and_linked_gate_original_seals_verified':True,'fresh_ownership_public_source_hashes_verified':True,
    'private_task_auth_token_exported':False}
(out/'collection-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),'files_verified':len(data['public_files']),
    'not_yet_present':data['not_yet_present'],'new_model_GUI_or_health_requests':0,'private_task_auth_token_exported':False}))
