"""Upload only the sealed public source/evidence package, never start a process."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'gui-preparation-package-02-f16dcef1024320e3.zip';raw=archive.read_bytes()
digest=hashlib.sha256(raw).hexdigest();assert digest=='fc7672688ca6c6e58e53c84077a4c9bfba2343c3771666d45f1feb7a590ca298'
stage='''import base64,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
raw=base64.b64decode(PAYLOAD)
assert hashlib.sha256(raw).hexdigest()==EXPECTED
dest=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-preparation-01')
dest.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw))as z:
    for name in z.namelist():
        path=PurePosixPath(name)
        assert not path.is_absolute()and'..'not in path.parts and'\\\\'not in name
        target=dest.joinpath(*path.parts)
        assert target.resolve().is_relative_to(dest.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as f:f.write(z.read(name))
seal=json.loads((dest/'package-seal.json').read_bytes())
assert set(seal['files'])=={str(p.relative_to(dest))for p in dest.rglob('*')if p.is_file()and p.name!='package-seal.json'}
for name,digest in seal['files'].items():assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
ready=json.loads((dest/'readiness.template.json').read_bytes())
config=json.loads((dest/'auxiliary-config.proposed.json').read_bytes())
assert ready['launch_ready']is False and config['deployment_applied']is False
assert config['token_created_by_this_package']is False
assert'primary_full_input_capacity'not in ready['evidence']and'ownership_transport'not in ready['evidence']
print(json.dumps({'remote':str(dest),'files_verified':len(seal['files'])+1,
    'package_seal_sha256':hashlib.sha256((dest/'package-seal.json').read_bytes()).hexdigest(),
    'launch_ready':False,'deployment_applied':False,'model_GUI_calls':0,'private_token_created':False}))
'''.replace('PAYLOAD',repr(base64.b64encode(raw).decode())).replace('EXPECTED',repr(digest))
cmd=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
     '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -']
r=subprocess.run(cmd,input=stage,text=True,capture_output=True,timeout=120)
evidence=ROOT/('gui-package-stage-receipt-'+str(time.time_ns()));evidence.mkdir()
(evidence/'stdout.txt').write_text(r.stdout,encoding='utf8');(evidence/'stderr.txt').write_text(r.stderr,encoding='utf8')
(evidence/'receipt.json').write_text(json.dumps({'returncode':r.returncode,'archive_sha256':digest,
    'remote':'/data/researcher/jev-defense-four-gpu-20261106/gui-preparation-01','automatic_retry':False},indent=2),encoding='utf8')
print(r.stdout);print(json.dumps({'local_receipt':str(evidence),'returncode':r.returncode}))
if r.returncode:raise SystemExit(r.returncode)
