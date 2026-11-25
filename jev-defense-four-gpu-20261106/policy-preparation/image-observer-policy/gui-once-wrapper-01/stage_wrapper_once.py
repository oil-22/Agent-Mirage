"""Upload only sealed public wrapper sources/CPU evidence; no GUI/model launch."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
archive=BASE/'stage-package-01-063d3890bc35d233.zip';raw=archive.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c31c672f39cf9c9e9ad2d3fe31b757bd1f686910570b0110633dafa0a70b7e40'
code='''import base64,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
raw=base64.b64decode(DATA)
assert hashlib.sha256(raw).hexdigest()=='c31c672f39cf9c9e9ad2d3fe31b757bd1f686910570b0110633dafa0a70b7e40'
root=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-01');root.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw))as z:
    for name in z.namelist():
        relative=PurePosixPath(name);assert not relative.is_absolute()and'..'not in relative.parts and'\\\\'not in name
        path=root.joinpath(*relative.parts);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as f:f.write(z.read(name))
seal=root/'wrapper-source-seal.json'
assert hashlib.sha256(seal.read_bytes()).hexdigest()=='063d3890bc35d2338de4bcd8fd95f1e188c40c3c949f711abe27b93a1fe1f5aa'
value=json.loads(seal.read_bytes())
for name,digest in value['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
print(json.dumps({'remote':str(root),'files_verified':len(value['files'])+1,'source_seal_sha256':hashlib.sha256(seal.read_bytes()).hexdigest(),'gui_once_sha256':value['gui_once_sha256'],'model_GUI_calls':0}))
'''.replace('DATA',repr(base64.b64encode(raw).decode()))
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -'],input=code,capture_output=True,text=True,timeout=120)
out=BASE/('stage-receipt-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stdout.txt').write_text(r.stdout,encoding='utf8');(out/'stderr.txt').write_text(r.stderr,encoding='utf8')
(out/'receipt.json').write_text(json.dumps({'returncode':r.returncode,'remote':'/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-01','model_GUI_calls':0}),encoding='utf8')
print(r.stdout);print(json.dumps({'returncode':r.returncode,'local':str(out)}))
if r.returncode:raise SystemExit(r.returncode)
