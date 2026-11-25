"""Bind the honest independent postexit map and run the unchanged real auditor."""
import base64,hashlib,json,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PYTHON='/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
CODE=r'''
import base64,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
MIRROR=BASE/'independent-service-postexit-mirror-1793983761231132390-gzip-linked02'
MANIFEST_SHA='eedd00633edb80b9f57ed81d1e899e564e38b0c5c2efbd6c44531c99a372e624'
RECEIPT_SHA='6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36'
LAUNCH_SHA='eda082227b74ddc005c1c7a2ffe0cfd8608bdac928817aa5a6b08a0a543d7dd8'
LAUNCH=BASE/'gui-final-readiness-retry01/launch-spec.json'
CONTROL=BASE/'gui-outer-control-retry01'
WRAPPER=BASE/'gui-once-wrapper-retry01/gui_once.py'
PYTHON=Path('/data/researcher/venvs/qwen35-9b-full-20261019/bin/python')
out=BASE/('gui-independent-postexit-integrity-audit-'+str(time.time_ns()))
out.mkdir(exist_ok=False);out.chmod(0o700)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,obj):
    with path.open('x',encoding='utf8')as f:json.dump(obj,f,indent=2)
assert sha(MIRROR/'receipt.json')==RECEIPT_SHA
preservation=json.loads((MIRROR/'receipt.json').read_bytes())
assert preservation['original_exit_json_missing']and preservation['original_terminal_sha256_missing']
assert preservation['worker_exit_codes']=={'primary':None,'pplx_flash':None}
assert preservation['actual_holder_launcher_return']['exit_code']==1
service=MIRROR/'service'
assert not(service/'terminal-sha256.json').exists()and not(service/'exit.json').exists()
argv=[str(PYTHON),'-B',str(WRAPPER),'audit-spec','--launch-spec',str(LAUNCH),
    '--launch-spec-sha256',LAUNCH_SHA,'--control-root',str(CONTROL),
    '--service-root',str(service),'--service-manifest-sha256',MANIFEST_SHA,
    '--output',str(out/'original-missing-terminal-audit-spec')]
original=subprocess.run(argv,capture_output=True,text=True)
(out/'original-audit-spec.stdout.txt').write_text(original.stdout,encoding='utf8')
(out/'original-audit-spec.stderr.txt').write_text(original.stderr,encoding='utf8')
save(out/'original-audit-spec-refusal.json',{'argv':argv,'returncode':original.returncode,
    'wrapper_source_sha256':sha(WRAPPER),'reason':'original fixed terminal-sha256.json absent; not fabricated'})
assert original.returncode!=0 and 'terminal-sha256.json'in original.stderr,'Original refusal differs; inspect before adapting'
sys.path.insert(0,str(WRAPPER.parent))
specmod=importlib.util.spec_from_file_location('original_gui_once_audit_helpers',WRAPPER)
module=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(module)
launch=module.bound(LAUNCH,LAUNCH_SHA);package=Path(launch['package']);module.validate_package(package)
batch=Path(launch['batch_root']);bm=CONTROL/'batch-postexit-sha256.json';cm=CONTROL/'postexit-sha256.json'
module.flat_manifest(CONTROL,cm,sha(cm));module.flat_manifest(batch,bm,sha(bm))
# The existing helper accepts an explicit external flat map. Its source and all
# per-file/exhaustive checks remain unchanged; no replacement file enters service.
manifest=MIRROR/'service-original-sha256.json'
mapping=module.flat_manifest(service,manifest,MANIFEST_SHA)
requests=[]
for role in ('primary','pplx_flash'):
    for request in sorted((service/role/'requests').iterdir()):
        if request.is_dir():requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':role})
for request in sorted((service/'transitions').iterdir()):
    if request.is_dir():requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':'primary'})
assert len(requests)==75
admission=service/'online-admission.json'
spec={'batch_root':str(batch),'plan':{'path':str(package/'plan.json'),'sha256':module.PLAN_SHA},
    'policy_source_seal':{'path':str(package/'policy-source-seal.json'),'sha256':module.POLICY_SEAL_SHA},
    'release_root':str(package/'release'),'runtime_admission':{'path':str(admission),'sha256':sha(admission)},
    'terminal_manifests':[{'root':str(batch),'path':str(bm),'sha256':sha(bm),'exhaustive':True},
        {'root':str(service),'path':str(manifest),'sha256':MANIFEST_SHA,'exhaustive':True}],
    'service_requests':requests,'service_journals':[{'path':str(service/'journal.jsonl'),'sha256':sha(service/'journal.jsonl')}],
    'independent_postexit_provenance':{'receipt':str(MIRROR/'receipt.json'),'receipt_sha256':RECEIPT_SHA,
        'original_service_terminal_manifest_missing':True,'original_service_exit_metadata_missing':True,
        'replacement_is_external_independent_preservation_not_original_terminal':True,
        'worker_exit_codes_unknown':True,'actual_launcher_exit_code':1,
        'original_missing_metadata_not_repaired_or_inferred':True}}
save(out/'audit-spec.json',spec)
auditor=package/'terminal-auditor/audit_gui_terminals.py'
env={**os.environ,'PYTHONPATH':str(package/'release'),'PYTHONDONTWRITEBYTECODE':'1'}
auditargv=[str(PYTHON),'-B',str(auditor),'--spec',str(out/'audit-spec.json'),'--output',str(out/'structural-audit')]
audit=subprocess.run(auditargv,capture_output=True,text=True,env=env)
(out/'actual-audit.stdout.txt').write_text(audit.stdout,encoding='utf8')
(out/'actual-audit.stderr.txt').write_text(audit.stderr,encoding='utf8')
result=json.loads((out/'structural-audit/audit.json').read_bytes())
receipt={'stage':'actual_structural_audit_with_explicit_independent_postexit_map',
    'root':str(out),'original_wrapper_refusal_preserved':True,'original_wrapper_returncode':original.returncode,
    'wrapper_source_sha256':sha(WRAPPER),'auditor_source_sha256':sha(auditor),
    'audit_argv':auditargv,'audit_returncode':audit.returncode,'audit_result':result,
    'audit_spec_sha256':sha(out/'audit-spec.json'),'postexit_preservation_receipt_sha256':RECEIPT_SHA,
    'independent_service_manifest_sha256':MANIFEST_SHA,'independent_service_manifest_files':len(mapping),
    'original_terminal_and_worker_exit_metadata_still_missing':True,
    'actual_launcher_exit_code':1,'worker_exit_codes_unknown':True,
    'metadata_failure_does_not_invalidate_verified_byte_bindings':True,
    'model_GUI_HTTP_scorer_or_signal_calls':0,'semantic_or_defense_effect_claim':False,'time':time.time()}
save(out/'receipt.json',receipt)
save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()})
public={}
for name in ('receipt.json','seal.json','audit-spec.json','original-audit-spec-refusal.json',
    'original-audit-spec.stdout.txt','original-audit-spec.stderr.txt','actual-audit.stdout.txt','actual-audit.stderr.txt',
    'structural-audit/audit.json','structural-audit/seal.json'):
    p=out/name;public[name]={'sha256':sha(p),'data':base64.b64encode(p.read_bytes()).decode()}
print(json.dumps({'root':str(out),'public':public}))
'''
if __name__=='__main__':
    out=ROOT/('service-postexit-integrity-audit-invocation-'+str(time.time_ns()));out.mkdir()
    (out/'source.py').write_text(CODE,encoding='utf8')
    run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',PYTHON+' -B -'],
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
        'full_inputs_or_auth_saved_locally':False},indent=2),encoding='utf8')
    receipt=json.loads((out/'receipt.json').read_bytes())
    print(json.dumps({'local':str(out),'remote_root':value['root'],'receipt_sha256':value['public']['receipt.json']['sha256'],
        'actual_audit_result':receipt['audit_result']}))
