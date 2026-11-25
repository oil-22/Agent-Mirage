"""Stage sealed public source bytes; do not execute prepare/run or call services."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ARCHIVE=HERE/'gui-migration-three-linked02-1dc3568fe5815748.zip'
ARCHIVE_SHA='48f8087a6eb427a98eaae6681deb45bcd353b8b6a9026b479646a4abecad6be6'
SEAL='1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44'
assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==ARCHIVE_SHA
CODE='ARCHIVE='+repr(base64.b64encode(ARCHIVE.read_bytes()).decode())+'\nARCHIVE_SHA='+repr(ARCHIVE_SHA)+'\nSEAL='+repr(SEAL)+'\n'+r'''
import base64,hashlib,io,json,sys,time,zipfile
from pathlib import Path
BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
root=BASE/'gui-migration-three-linked02';assert not root.exists(),'Preserve an existing/failed stage; never overwrite'
raw=base64.b64decode(ARCHIVE);assert hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA
root.mkdir();root.chmod(0o700)
with zipfile.ZipFile(io.BytesIO(raw))as z:
    for info in z.infolist():
        rel=Path(info.filename);assert not rel.is_absolute()and '..'not in rel.parts
        p=(root/rel);assert p.resolve().is_relative_to(root.resolve())
        if info.is_dir():p.mkdir(parents=True,exist_ok=True);continue
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb')as f:f.write(z.read(info))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'package-seal.json')==SEAL
mapping=json.loads((root/'package-seal.json').read_bytes())
assert {p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p!=root/'package-seal.json'}==set(mapping)
for name,value in mapping.items():assert sha(root/name)==value
sys.path.insert(0,str(root));import gui_once
gui_once.validate_package(root,SEAL)
module=gui_once.module(root);proof=json.loads((root/'three-trajectory-migration-source.json').read_bytes())
assert module.validate_migration_source(proof)is True
ready=json.loads((root/'readiness.template.json').read_bytes());assert ready['launch_ready']is False
assert sha(root/'evidence/primary-capacity/receipt.json')=='fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
out=BASE/('gui-three-package-stage-'+str(time.time_ns()));out.mkdir();out.chmod(0o700)
receipt={'stage':'exact_three_source_package_only','package':str(root),'package_seal_sha256':SEAL,
    'archive_sha256':ARCHIVE_SHA,'archive_bytes':len(raw),'all_files_verified':len(mapping),
    'wrapper_source_sha256':sha(root/'gui_once.py'),'source_policy_seal_sha256':sha(root/'policy-source-seal.json'),
    'exact_old_unspent_source_reverified':True,'actual_capacity21470_receipt_mirrored':True,
    'new_private_token_not_read_or_copied_by_stager':True,'readiness_launch_ready':False,
    'model_GUI_HTTP_scorer_signal_calls':0,'prepare_run_or_background_invoked':False,'time':time.time()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({'receipt.json':sha(out/'receipt.json')},indent=2),encoding='utf8')
print(json.dumps({'receipt_root':str(out),'receipt':receipt,'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}))
'''
out=ROOT/('gui-three-package-stage-invocation-'+str(time.time_ns()));out.mkdir()
(out/'source.py').write_text(CODE,encoding='utf8')
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=CODE,capture_output=True,text=True,timeout=90)
(out/'stderr.txt').write_text(r.stderr,encoding='utf8');(out/'stdout.txt').write_text(r.stdout,encoding='utf8')
if r.returncode:raise SystemExit(r.returncode)
data=json.loads(r.stdout);(out/'receipt.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({'local':str(out),**data}))
