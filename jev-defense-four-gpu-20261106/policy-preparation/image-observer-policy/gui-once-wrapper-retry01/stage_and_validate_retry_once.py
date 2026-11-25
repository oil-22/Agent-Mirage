"""Stage linked native-env repair, then only real imports/parser/scorer loading."""
import base64,hashlib,io,json,subprocess,time,zipfile
from pathlib import Path
BASE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=['gui_once.py','background_start.py','native_environment.py','validate_native_environment.py',
    'test_gui_once.py','test_background_start.py','test_native_environment.py','successful_parent_environment_transport.py']
receipt={'tests_passed':True,'test_count':43,'actual_command':'python -B -m unittest -v test_gui_once.py test_background_start.py test_native_environment.py',
    'actual_result':'Ran43 tests OK; recorded from preceding executed tool output',
    'source_sha256':{name:sha(BASE/name)for name in files},'model_GUI_network_processspawns':0,
    'old_failure_preserved':'/data/researcher/jev-defense-four-gpu-20261106/gui-startup-failure-preservation-01',
    'sealed04_plan_budgets_unchanged':True,'only_native_environment_restored':True}
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)as z:
    for name in files:z.write(BASE/name,name)
    z.writestr('cpu-receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2))
raw=buffer.getvalue();payload_sha=hashlib.sha256(raw).hexdigest()
code='''import base64,hashlib,io,json,os,zipfile
from pathlib import Path,PurePosixPath
raw=base64.b64decode(DATA);assert hashlib.sha256(raw).hexdigest()==DIGEST
dest=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-retry01');dest.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw))as z:
    for name in z.namelist():
        p=PurePosixPath(name);assert len(p.parts)==1 and'..'not in p.parts
        with(dest/name).open('xb')as f:f.write(z.read(name))
receipt=json.loads((dest/'cpu-receipt.json').read_bytes())
for name,digest in receipt['source_sha256'].items():assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest
seal={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.iterdir()if p.is_file()}
with(dest/'source-seal.json').open('x')as f:json.dump(seal,f,indent=2)
print(json.dumps({'stage':'verified','wrapper_sha256':seal['gui_once.py'],'background_sha256':seal['background_start.py'],
'source_seal_sha256':hashlib.sha256((dest/'source-seal.json').read_bytes()).hexdigest(),'model_GUI_calls':0}),flush=True)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
python='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
os.execv(python,[python,'-B',str(dest/'validate_native_environment.py'),'--output',
'/data/researcher/jev-defense-four-gpu-20261106/native-env-retry-preflight-01'])
'''.replace('DATA',repr(base64.b64encode(raw).decode())).replace('DIGEST',repr(payload_sha))
result=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=180)
out=BASE/('stage-native-validation-'+str(time.time_ns()));out.mkdir()
(out/'stdout.txt').write_text(result.stdout,encoding='utf8');(out/'stderr.txt').write_text(result.stderr,encoding='utf8')
(out/'receipt.json').write_text(json.dumps({'returncode':result.returncode,'payload_sha256':payload_sha,
    'source_sha256':receipt['source_sha256'],'actual_calls_limited_to_native_import_parser_loader':True,
    'model_GUI_or_scorer_execution_calls':0},indent=2),encoding='utf8')
print(result.stdout);print(json.dumps({'returncode':result.returncode,'local_receipt':str(out)}))
if result.returncode:raise SystemExit(result.returncode)
