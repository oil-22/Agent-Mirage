"""Stage sources and check Linux imports/denial paths; NEVER submit a job."""
import base64
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from control import remote


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not (HERE / 'CPU-stage-linked03-current.json').exists(), 'Do not repeat a staged CPU check'
    package = HERE / 'package-linked03'
    manifest = json.loads((package/'execution-manifest.json').read_bytes())
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as z:
        for name, expected in manifest['files'].items():
            assert sha(package/name)==expected,name
            z.writestr(name,(package/name).read_bytes())
        z.writestr('execution-manifest.json',(package/'execution-manifest.json').read_bytes())
    code = ('ROOT='+repr(manifest['remote_package'])+'\nEXPECTED='+repr(sha(package/'execution-manifest.json'))+'\n'+r'''
import ast,base64,hashlib,io,json,os,sys,time,zipfile
from pathlib import Path
assert os.getuid()==1033
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='4'
root=Path(ROOT);root.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD,validate=True)))as z:
 for name in z.namelist():
  p=root/name;assert p.resolve().is_relative_to(root.resolve());p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(z.read(name))
assert sha(root/'execution-manifest.json')==EXPECTED
manifest=json.loads((root/'execution-manifest.json').read_bytes())
for name,h in manifest['files'].items():
 assert sha(root/name)==h,name
 if name.endswith('.py'):ast.parse((root/name).read_text())
assert not(root/'authorization.json').exists()
assert not Path(manifest['output']).exists()
sys.path.insert(0,str(root))
import offline_worker,offline_launcher,primary_server,preflight_support,memory_lifetime,mlp_lifetime
from defense.qwen_backend import LocalQwen
assert 'torch'not in sys.modules
cases=offline_worker.bind_cases(manifest)
assert len(cases)==10
evidence=root/'CPU-boundary-evidence';evidence.mkdir()
checks=[{'name':'unchanged_native_dependency_modules_import_without_torch','passed':True},
 {'name':'all10_frozen_complete_source_and_native_CPU_wrapper_bindings','passed':True},
 {'name':'no_real_authorization_or_output_root_exists','passed':True}]
saved_argv=sys.argv[:]
for module in [offline_worker,offline_launcher]:
 sys.argv=[str(root/(module.__name__+'.py'))]
 try:module.main()
 except RuntimeError as exc:
  assert 'authorization'in str(exc).lower()
 else:raise AssertionError('Missing-authorization CLI did not reject')
 checks.append({'name':module.__name__+'_missing_real_authorization_denied_before_load','passed':True})
sys.argv=saved_argv
try:offline_worker.validate_package(evidence/'no-such-approval.json','0'*64)
except FileNotFoundError:pass
else:raise AssertionError('Nonexistent approval accepted')
checks.append({'name':'nonexistent_approval_denied_before_native_model_import','passed':True})
for name,changes in [
 ('old_ten_call_scope',{'authorized':True,'exact_answer':'批准10条离线开发预检（推荐）'}),
 ('CPU_fixture_is_not_human_approval',{'authorized':True,'source':'CPU_fixture'})]:
 value={'authorized':False,'exact_answer':'批准20次离线开发预检（推荐）',
  'condition':'same-primary-history-image-preread-v1','proposal_seal_sha256':manifest['proposal_seal_sha256'],
  'new_primary_calls_cap':20,'phase_output_caps':{'preread':4096,'actor':2048},
  'GUI_Flash_scorer_paid_calls':0,'automatic_retries':0,'formal_GUI_authorized':False,
  'source':'CPU_fixture','human_reply_receipt_sha256':'CPU-only-not-real',
  'study_claim_root':manifest['study_claim_root'],**changes}
 p=evidence/(name+'.json')
 with p.open('x')as f:json.dump(value,f)
 try:offline_worker.validate_package(p,sha(p))
 except RuntimeError:pass
 else:raise AssertionError('Unapproved scope accepted')
 checks.append({'name':name+'_denied','passed':True})
assert 'torch'not in sys.modules and not Path(manifest['output']).exists()
result={'time':time.time(),'checks':checks,'passed':len(checks),'files':len(manifest['files']),
 'manifest_sha256':EXPECTED,'bound_source_cases':len(cases),'torch_imported':False,
 'real_authorization_created':False,'new_GPU_lease_acquired':False,'locks_acquired':False,
 'model_loader_or_generate_called':False,'model_GPU_GUI_Flash_scorer_calls':0,
 'formal_runtime_forward_and_capacity_NOT_TESTED':True,'no_command_or_old_queue_submitted':True}
with(evidence/'result.json').open('x')as f:json.dump(result,f,indent=2)
with(evidence/'seal.json').open('x')as f:json.dump({p.name:sha(p)for p in evidence.iterdir()if p.is_file()},f,indent=2)
print(json.dumps({'result':result,'remote_evidence':str(evidence),'remote_seal_sha256':sha(evidence/'seal.json')}))
''')
    raw,op=remote('3090',code,'stage-preread-memory-linked03-source-only-denial-CPU',timeout=55,
                  private_prefix='PAYLOAD='+repr(base64.b64encode(stream.getvalue()).decode())+'\n')
    result=json.loads(raw)
    dest=HERE/('Linux-CPU-stage-linked03-'+str(time.time_ns()));dest.mkdir()
    (dest/'source.py').write_bytes(Path(__file__).read_bytes())
    with(dest/'result.json').open('x',encoding='utf8')as f:
        json.dump({'operation':str(op),**result},f,ensure_ascii=False,indent=2)
    with(dest/'seal.json').open('x',encoding='utf8')as f:
        json.dump({p.name:sha(p)for p in dest.iterdir()if p.is_file()},f,indent=2)
    with(HERE/'CPU-stage-linked03-current.json').open('x',encoding='utf8')as f:
        json.dump({'root':str(dest),'seal_sha256':sha(dest/'seal.json')},f,indent=2)
    print(json.dumps({'stage':str(dest),'CPU_checks':result['result']['passed'],
                      'new_model_GPU_GUI_calls':0,'authorized_or_submitted':False}))


if __name__=='__main__':
    main()
