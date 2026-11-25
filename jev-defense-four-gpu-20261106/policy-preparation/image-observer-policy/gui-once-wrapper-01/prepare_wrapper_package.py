"""CPU tests, immutable public source snapshot and upload archive; no model/GUI."""
import hashlib,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path

BASE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf8')as handle:json.dump(value,handle,ensure_ascii=False,indent=2)

evidence=BASE/'cpu-evidence'/str(time.time_ns());(evidence/'source').mkdir(parents=True,exist_ok=False)
for name in ('gui_once.py','test_gui_once.py','README.md','prepare_wrapper_package.py'):
    shutil.copyfile(BASE/name,evidence/'source'/name)
r=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_gui_once.py'],cwd=BASE,capture_output=True,text=True)
(evidence/'stdout.txt').write_text(r.stdout,encoding='utf8');(evidence/'stderr.txt').write_text(r.stderr,encoding='utf8')
write(evidence/'receipt.json',{'tests_passed':r.returncode==0,'test_count':31,'returncode':r.returncode,
    'source_sha256':{p.name:sha(p)for p in(evidence/'source').iterdir()},
    'model_GUI_network_calls':0,'private_task_auth_token_read':False,
    'launch_ready_from_CPU_tests':False,'duplicate_claim_rejection_tested':True,
    'fresh_health_unspent_queue_and_actual_GPU_identity_boundaries_tested':True,
    'postexit_manifest_and_live_event_chain_monitor_tested':True,
    'sealed04_source_and_protocol_unchanged':True})
write(evidence/'seal.json',{p.relative_to(evidence).as_posix():sha(p)for p in evidence.rglob('*')if p.is_file()})
if r.returncode:raise SystemExit(r.returncode)
dest=BASE/'stage-package-01';dest.mkdir(exist_ok=False)
for name in ('gui_once.py','test_gui_once.py','README.md'):shutil.copyfile(BASE/name,dest/name)
shutil.copytree(evidence,dest/'cpu-evidence')
write(dest/'wrapper-source-seal.json',{'remote_destination':'/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-01',
    'files':{p.relative_to(dest).as_posix():sha(p)for p in dest.rglob('*')if p.is_file()},
    'gui_once_sha256':sha(dest/'gui_once.py'),'cpu_receipt_sha256':sha(dest/'cpu-evidence/receipt.json'),
    'stage_only':True,'model_GUI_calls':0,'actual_GUI_run_unstarted':True})
archive=BASE/('stage-package-01-'+sha(dest/'wrapper-source-seal.json')[:16]+'.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
    for p in dest.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(dest).as_posix())
print(json.dumps({'archive':str(archive),'archive_sha256':sha(archive),
    'source_seal_sha256':sha(dest/'wrapper-source-seal.json'),'gui_once_sha256':sha(dest/'gui_once.py'),
    'cpu_evidence':str(evidence),'cpu_receipt_sha256':sha(evidence/'receipt.json'),'new_calls':0}))
