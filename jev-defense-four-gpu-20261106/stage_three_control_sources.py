"""Stage only sealed control helper bytes; never invoke their prepare/run mains."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'gui-three-control-preparation-01'
SEAL='db723d2f2b4b24c1dd2085d40fe3f56db8f61f9b411a4791ea1d95a72764956a'
assert hashlib.sha256((SOURCE/'seal.json').read_bytes()).hexdigest()==SEAL
mapping=json.loads((SOURCE/'seal.json').read_bytes())
payload={name:base64.b64encode((SOURCE/name).read_bytes()).decode()for name in list(mapping)+['seal.json']}
CODE='FILES='+repr(payload)+'\nSEAL='+repr(SEAL)+'\n'+r'''
import base64,hashlib,json,os,time
from pathlib import Path
BASE=Path('/data/researcher/jev-defense-four-gpu-20261106');root=BASE/'gui-three-control-preparation-01'
assert os.getuid()==1015 and not root.exists()
root.mkdir();root.chmod(0o700)
for name,data in FILES.items():
    rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(base64.b64decode(data))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'seal.json')==SEAL
mapping=json.loads((root/'seal.json').read_bytes())
assert {p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p!=root/'seal.json'}==set(mapping)
for name,value in mapping.items():assert sha(root/name)==value
for p in root.glob('*.py'):compile(p.read_text(encoding='utf8'),str(p),'exec')
out=BASE/('gui-three-control-source-stage-'+str(time.time_ns()));out.mkdir()
receipt={'stage':'sealed_control_source_only','root':str(root),'seal_sha256':SEAL,'files_verified':len(mapping),
    'prepare_helper_sha256':sha(root/'prepare_bound_once.py'),'background_helper_sha256':sha(root/'background_three_once.py'),
    'sealed_GUI_package_not_modified':True,'actual_prepare_run_health_POST_model_GUI_scorer_signal_calls':0,'time':time.time()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({'receipt.json':sha(out/'receipt.json')},indent=2),encoding='utf8')
print(json.dumps({'receipt_root':str(out),'receipt':receipt,'receipt_sha256':sha(out/'receipt.json')}))
'''
out=ROOT/('gui-three-control-stage-invocation-'+str(time.time_ns()));out.mkdir()
(out/'source.py').write_text(CODE,encoding='utf8')
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=CODE,capture_output=True,text=True,timeout=90)
(out/'stderr.txt').write_text(r.stderr,encoding='utf8');(out/'stdout.txt').write_text(r.stdout,encoding='utf8')
if r.returncode:raise SystemExit(r.returncode)
value=json.loads(r.stdout);(out/'receipt.json').write_text(json.dumps(value,indent=2),encoding='utf8')
print(json.dumps({'local':str(out),**value}))
