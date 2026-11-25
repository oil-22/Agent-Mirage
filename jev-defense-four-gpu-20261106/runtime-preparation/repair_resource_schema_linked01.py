"""Add only exact source-bound group/spec schema fields; no health/collector/GUI."""
import base64,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE=Path(__file__).parents[1]
failed=BASE/'actual-three-GUI-start-01';mapping=json.loads((failed/'seal.json').read_bytes())
for name,expected in mapping.items():assert hashlib.sha256((failed/name).read_bytes()).hexdigest()==expected
failure_files={name:base64.b64encode((failed/name).read_bytes()).decode()for name in list(mapping)+['seal.json']}
actual=json.loads(remote(r'''
import base64,hashlib,json,time
from pathlib import Path
G=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799')
state=json.loads((G/'online-state.json').read_bytes())
assert state['phase']=='ready'and state['active']is None and state['next_run_index']==0and len(state['runs'])==3
assert all(r['status']=='not_started'and r['calls']=={'actor':0,'judge':0,'observe':0}for r in state['runs'].values())
assert all(not list((G/role/'requests').iterdir())for role in('primary','pplx_flash'))and not list((G/'transitions').iterdir())
print(json.dumps({'group':str(G),'time':time.time(),'actual_state':state,
 'state_sha256':hashlib.sha256((G/'online-state.json').read_bytes()).hexdigest(),
 'primary_requests':0,'helper_requests':0,'transitions':0,'model_GUI_health_collector_calls':0}))
''',timeout=180,host='3090'))
code=r'''
import base64,hashlib,importlib.util,json,time
from pathlib import Path
B=Path('/data/researcher/jev-defense-four-gpu-20261106')
old=B/'online-three-resource-conditions/1793986896126859644/resource-conditions.json'
audit=B/'online-three-independent-audits/1793986896126859644/receipt.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
assert sha(old)=='5dbb2b6d459d479d4c8f687e166f9835ae927a0d1c6bca95786707d629890c64'
assert sha(audit)=='fd1701a0872a982e3bf8491068ace77840bcdba45e1bc9a0c7b2179f6ea900b0'
original=read(old);source=read(audit)
assert 'group'not in original and 'reviewed_spec_sha256'not in original
new={**original,'group':source['group'],'reviewed_spec_sha256':source['specification_sha256']}
assert set(new)-set(original)=={'group','reviewed_spec_sha256'}and all(new[k]==v for k,v in original.items())
root=B/'online-three-resource-schema-linked'/str(time.time_ns());root.mkdir(parents=True,exist_ok=False)
def save(name,value):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(value,f,indent=2)
for name,encoded in FAILED_FILES.items():
 p=root/'old-GUI-start-public'/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(encoded))
oldmap=read(root/'old-GUI-start-public/seal.json')
for name,expected in oldmap.items():assert sha(root/'old-GUI-start-public'/name)==expected
save('resource-conditions.json',new);save('actual3090-unspent.json',ACTUAL)
assert ACTUAL['group']==source['group']and ACTUAL['primary_requests']==0and ACTUAL['helper_requests']==0and ACTUAL['transitions']==0
names=['gui-three-evidence-binding-01','gui-final-readiness-three-01','gui-batch-image-observer-three-01',
 'gui-outer-control-three-01','gui-outer-background-three-01',
 'gui-final-readiness-three-01/launch-claimed.json','gui-final-readiness-three-01/launch-spec.json',
 'gui-three-evidence-binding-01/preparation-claim.json','gui-three-evidence-binding-01/evidence-bindings.json']
absent={name:not(B/name).exists()for name in names};assert all(absent.values()),absent
save('actual4090-no-GUI-claims.json',{'time':time.time(),'absent':absent,'all_absent':True,
 'GUI_binding_readiness_background_control_claim_created':False,'health_model_GUI_collector_calls':0})
control=B/'gui-three-control-preparation-01'
assert sha(control/'seal.json')=='db723d2f2b4b24c1dd2085d40fe3f56db8f61f9b411a4791ea1d95a72764956a'
controlmap=read(control/'seal.json')
for name,expected in controlmap.items():assert sha(control/name)==expected
spec=importlib.util.spec_from_file_location('sealed_actual_prepare_bound_once',control/'prepare_bound_once.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.validate_resource(read(root/'resource-conditions.json'))
for name,expected in controlmap.items():assert sha(control/name)==expected
assert all(not(B/name).exists()for name in names)
assert sha(old)=='5dbb2b6d459d479d4c8f687e166f9835ae927a0d1c6bca95786707d629890c64'
save('receipt.json',{'status':'passed_source_bound_two_fields_only','resource':str(root/'resource-conditions.json'),
 'resource_sha256':sha(root/'resource-conditions.json'),'old_resource':str(old),'old_resource_sha256':sha(old),
 'source_actual_audit':str(audit),'source_actual_audit_sha256':sha(audit),
 'added_fields':{'group':new['group'],'reviewed_spec_sha256':new['reviewed_spec_sha256']},
 'all_previous_fields_unchanged':True,'actual_sealed_helper_validate_resource_passed':True,
 'sealed_package_and_helpers_unchanged':True,'all_new_model_GUI_requests_and_claims_zero':True,
 'new_collector_health_model_GUI_calls':0})
save('seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
print(json.dumps({'root':str(root),'receipt_sha256':sha(root/'receipt.json'),'seal_sha256':sha(root/'seal.json'),
 'resource':str(root/'resource-conditions.json'),'resource_sha256':sha(root/'resource-conditions.json'),
 'files':{str(p.relative_to(root)):base64.b64encode(p.read_bytes()).decode()for p in root.rglob('*')if p.is_file()}}))
'''
result=json.loads(remote('FAILED_FILES='+repr(failure_files)+'\nACTUAL='+repr(actual)+'\n'+code,timeout=180,host='4090'))
files=result.pop('files');local=BASE/'resource-schema-linked-evidence'/Path(result['root']).name
local.mkdir(parents=True,exist_ok=False);seal=json.loads(base64.b64decode(files['seal.json']))
for name,encoded in files.items():
 raw=base64.b64decode(encoded)
 if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
 path=local/name;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as f:f.write(raw)
print(json.dumps({'local':str(local),**result}))
