"""Preserve the first spec-builder failure; handle an honestly empty mirror dir."""
import base64,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
prior=HERE/'audit_stopped_independent.py'
spec=importlib.util.spec_from_file_location('audit_builder_prior',prior)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
before="""for role in ('primary','pplx_flash'):
    for request in sorted((service/role/'requests').iterdir()):
        if request.is_dir():requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':role})"""
after="""for role in ('primary','pplx_flash'):
    request_dir=service/role/'requests'
    if not request_dir.exists():
        assert role=='pplx_flash' and preservation['request_counts'][role]=={'completed':0,'failed':0,'pending_unsealed':0}
        assert not any(name.startswith(role+'/requests/')for name in mapping)
        continue
    for request in sorted(request_dir.iterdir()):
        if request.is_dir():requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':role})"""
assert old.CODE.count(before)==1
CODE=old.CODE.replace(before,after)
CODE=CODE.replace("'worker_exit_codes_unknown':True,'actual_launcher_exit_code':1,",
    "'worker_exit_codes_unknown':True,'actual_launcher_exit_code':1,'empty_observer_request_directory_not_preserved_but_zero_native_requests_proven':True,")
out=ROOT/('service-postexit-integrity-audit-linked02-invocation-'+str(time.time_ns()));out.mkdir()
(out/'prior-source.py').write_bytes(prior.read_bytes())
(out/'source.py').write_text(CODE,encoding='utf8')
run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',old.PYTHON+' -B -'],
    input=CODE,capture_output=True,text=True,timeout=240)
(out/'stderr.txt').write_text(run.stderr,encoding='utf8')
if run.returncode:
    (out/'stdout.failure.txt').write_text(run.stdout,encoding='utf8');raise SystemExit(run.returncode)
value=json.loads(run.stdout)
for name,item in value['public'].items():
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
    path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
(out/'delivery.json').write_text(json.dumps({'remote_root':value['root'],
    'public_sha256':{n:i['sha256']for n,i in value['public'].items()},
    'prior_builder_failure_preserved':True,'full_inputs_or_auth_saved_locally':False},indent=2),encoding='utf8')
receipt=json.loads((out/'receipt.json').read_bytes())
print(json.dumps({'local':str(out),'remote_root':value['root'],'receipt_sha256':value['public']['receipt.json']['sha256'],
    'actual_audit_result':receipt['audit_result']}))
