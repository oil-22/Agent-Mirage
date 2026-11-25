"""Validate the exact old unspent evidence on4090; no models/HTTP/GUI/signals."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
files={n:base64.b64encode((HERE/n).read_bytes()).decode()for n in
    ('release/migration_contract.py','release/frozen-original-plan.json','three-trajectory-migration-source.json')}
CODE='FILES='+repr(files)+'\n'+r'''
import base64,hashlib,importlib.util,json,sys,time
from pathlib import Path
out=Path('/data/researcher/jev-defense-four-gpu-20261106')/('three-trajectory-unspent-source-audit-'+str(time.time_ns()))
out.mkdir();out.chmod(0o700)
for name,data in FILES.items():
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
spec=importlib.util.spec_from_file_location('exact_three_migration',out/'release/migration_contract.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
proof=json.loads((out/'three-trajectory-migration-source.json').read_bytes())
passed=module.validate_migration_source(proof);assert passed is True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt={'stage':'actual_fixed_original_unspent_source_CPU_audit','source_unspent_verified':True,
    'old_terminal_failure_and_unknown_worker_exit_preserved':True,'actual_migrated_service_begins':0,
    'actual_migrated_service_model_calls':0,'actual_migrated_GUI_attempts':0,'exact_original_three_run_suffix':True,
    'maximum_new_primary_calls':630,'maximum_new_auxiliary_calls':120,'old_failed_baseline_not_reexecuted':True,
    'proof_sha256':sha(out/'three-trajectory-migration-source.json'),'source_sha256':sha(out/'release/migration_contract.py'),
    'actual_source_checks':'fixed state SHA; 150-chain no migratedIDs; original full GUI file inventory+no attempts; actual old structure audit; original stop failure',
    'launch_ready':False,'model_GUI_HTTP_scorer_signal_calls':0,'time':time.time()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(out),'receipt':receipt,'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}))
'''
out=HERE/'actual-source-audit'/str(time.time_ns());out.mkdir(parents=True)
(out/'source.py').write_text(CODE,encoding='utf8')
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=CODE,capture_output=True,text=True,timeout=90)
(out/'stderr.txt').write_text(r.stderr,encoding='utf8');(out/'stdout.txt').write_text(r.stdout,encoding='utf8')
if r.returncode:raise SystemExit(r.returncode)
value=json.loads(r.stdout)
(out/'receipt.json').write_text(json.dumps(value,indent=2),encoding='utf8')
print(json.dumps({'local':str(out),**value}))
