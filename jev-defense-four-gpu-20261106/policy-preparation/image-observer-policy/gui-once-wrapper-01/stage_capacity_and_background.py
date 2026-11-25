"""Public capacity identity + new background helper upload; never starts GUI."""
import base64,hashlib,io,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
BASE=Path(__file__).resolve().parent
CAP=BASE.parents[2]/'online-evidence-receipts/1793978373849279400/capacity'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)

assert sha(CAP/'receipt.json')=='5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8'
for name,digest in json.loads((CAP/'seal.json').read_bytes()).items():assert sha(CAP/name)==digest
evidence=BASE/'background-cpu-evidence'/str(time.time_ns());evidence.mkdir(parents=True)
r=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_background_start.py'],cwd=BASE,capture_output=True,text=True)
(evidence/'stdout.txt').write_text(r.stdout,encoding='utf8');(evidence/'stderr.txt').write_text(r.stderr,encoding='utf8')
for name in('background_start.py','test_background_start.py'):shutil.copyfile(BASE/name,evidence/name)
write(evidence/'receipt.json',{'tests_passed':r.returncode==0,'test_count':6,'model_GUI_network_processspawns':0,
    'background_helper_sha256':sha(BASE/'background_start.py'),'automatic_retries':False})
write(evidence/'seal.json',{p.name:sha(p)for p in evidence.iterdir()if p.is_file()})
assert r.returncode==0
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)as z:
    for p in CAP.iterdir():
        if p.is_file():z.write(p,'capacity/'+p.name)
    for p in evidence.iterdir():
        if p.is_file():z.write(p,'background/'+p.name)
raw=buffer.getvalue();digest=hashlib.sha256(raw).hexdigest()
code='''import base64,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
raw=base64.b64decode(DATA);assert hashlib.sha256(raw).hexdigest()==DIGEST
roots={'capacity':Path('/data/researcher/jev-defense-four-gpu-20261106/primary-capacity-independent-evidence-01'),
'background':Path('/data/researcher/jev-defense-four-gpu-20261106/gui-background-helper-01')}
for root in roots.values():root.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw))as z:
    for name in z.namelist():
        p=PurePosixPath(name);assert len(p.parts)==2 and'..'not in p.parts
        target=roots[p.parts[0]]/p.parts[1]
        with target.open('xb')as f:f.write(z.read(name))
for root in roots.values():
    for name,digest in json.loads((root/'seal.json').read_bytes()).items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
print(json.dumps({'capacity_receipt':str(roots['capacity']/'receipt.json'),
'capacity_sha256':hashlib.sha256((roots['capacity']/'receipt.json').read_bytes()).hexdigest(),
'background_helper':str(roots['background']/'background_start.py'),
'background_helper_sha256':hashlib.sha256((roots['background']/'background_start.py').read_bytes()).hexdigest(),
'actual_GUI_or_model_started':False}))
'''.replace('DATA',repr(base64.b64encode(raw).decode())).replace('DIGEST',repr(digest))
result=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=120)
receipt=BASE/('background-capacity-stage-'+str(time.time_ns()));receipt.mkdir()
(receipt/'stdout.txt').write_text(result.stdout,encoding='utf8');(receipt/'stderr.txt').write_text(result.stderr,encoding='utf8')
write(receipt/'receipt.json',{'returncode':result.returncode,'payload_sha256':digest,
    'background_cpu_receipt_sha256':sha(evidence/'receipt.json'),'actual_GUI_or_model_started':False})
print(result.stdout);print(json.dumps({'local_stage_receipt':str(receipt),'returncode':result.returncode}))
if result.returncode:raise SystemExit(result.returncode)
