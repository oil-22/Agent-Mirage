"""Preserve actual audit sources and export passed public evidence; no live calls."""
import base64,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
here=Path(__file__).resolve().parent
sources={name:base64.b64encode((here/name).read_bytes()).decode()for name in('audit_controller_remote.py','run_controller_audit.py','collect_service_remote.py','run_collect.py')}
code=r'''
import base64,hashlib,json,time
from pathlib import Path
B=Path('/data/researcher/jev-defense-four-gpu-20261106')
original=B/'first-online-observer-engineering/1793987824387139334'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(original/'receipt.json')=='9b7bebd012f273a172be22b423221722af9bc7d94822d25f1fa65b136b582f2a'
seal=json.loads((original/'seal.json').read_bytes())
for name,expected in seal.items():assert sha(original/name)==expected
root=B/'first-online-observer-audit-finalization'/str(time.time_ns());root.mkdir(parents=True,exist_ok=False)
for name,encoded in SOURCES.items():
 with(root/name).open('xb')as f:f.write(base64.b64decode(encoded))
def save(name,value):
 with(root/name).open('x')as f:json.dump(value,f,indent=2)
failed=[str(p)for p in(B/'first-online-observer-engineering').iterdir()if p.is_dir()and not(p/'receipt.json').exists()]
save('prior-audit-only-import-failure.json',{'failed_output_roots':failed,
 'reported_original_error':'ModuleNotFoundError: No module named numpy while importing image_observer -> defense.core in systempython',
 'repair':'Read exact current constants using AST literal_eval; verify source SHA against real implementation event; no model/native source change',
 'failed_model_health_GUI_POST_calls':0,'original_partial_outputs_preserved':True,
 'original_first_failed_raw_script_not_available_as_saved_file':True})
save('receipt.json',{'status':'passed_engineering_public_finalization','actual_audit':str(original/'receipt.json'),
 'actual_audit_sha256':sha(original/'receipt.json'),'actual_audit_seal_sha256':sha(original/'seal.json'),
 'actual_auditor_source_sha256':sha(root/'audit_controller_remote.py'),
 'actual_service_collection':'/home/researcher/jev-defense-four-gpu-20261106/first-online-observer-engineering/1793987640839997700/collection.json',
 'native_processor_or_softmax_recompute_not_performed':True,'semantic_labels_or_execution_join_not_performed':True,
 'private_event_values_not_inspected_or_exported':True,'new_model_health_GUI_POST_calls':0,
 'original_service_pending_requests_not_read':True,'actual_passed_audit_bytes_unchanged':True})
save('seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
print(json.dumps({'original_root':str(original),'finalization_root':str(root),'finalization_receipt_sha256':sha(root/'receipt.json'),
 'finalization_seal_sha256':sha(root/'seal.json'),
 'groups':{'actual':{name:base64.b64encode((original/name).read_bytes()).decode()for name in list(seal)+['seal.json']},
 'finalization':{p.name:base64.b64encode(p.read_bytes()).decode()for p in root.iterdir()if p.is_file()}}}))
'''
value=json.loads(remote('SOURCES='+repr(sources)+'\n'+code,timeout=180,host='4090'))
groups=value.pop('groups');root=here.parents[1]/'first-online-observer-engineering-public/1793987824387139334'
root.mkdir(parents=True,exist_ok=False)
count=0
for group,records in groups.items():
 seal=json.loads(base64.b64decode(records['seal.json']))
 for name,encoded in records.items():
  raw=base64.b64decode(encoded)
  if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
  path=root/group/name;path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb')as f:f.write(raw)
  count+=1
print(json.dumps({'local':str(root),'public_files_SHA_verified':count,**value}))
