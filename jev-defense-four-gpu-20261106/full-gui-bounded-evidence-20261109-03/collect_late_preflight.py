import base64
import json
from remote_control import HERE,ROOT4090,remote,save,sha

code='ROOT='+repr(ROOT4090)+'\n'+r'''
from pathlib import Path
import hashlib,json,base64,time
r=Path(ROOT);p=r/'environment-preflight';receipt=json.loads((p/'receipt.json').read_bytes());assert receipt['status']=='passed'
assert not Path('/proc/2357272').exists(),'Original slow preflight must have exited before collection'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=r/'environment-preflight-completion-01';target.mkdir(exist_ok=False)
files={str(v.relative_to(p)):sha(v)for v in sorted(p.rglob('*'))if v.is_file()}
result={'late_original_attempt_completed':True,'original_process_exited_verified':True,'original_pid':2357272,
 'observed_interim_UID':1015,'observed_interim_start_ticks':'118648434',
 'observed_interim_blocking':'D state wait_on_page_bit_common reading original openai beta .pyc during import',
 'no_retry_or_condition_change':True,'receipt':receipt,'original_files_SHA':files,'models_GUI_scorer_calls':0}
(target/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'audit':result,'audit_sha256':sha(target/'audit.json'),
 'public_files':{n:base64.b64encode((p/n).read_bytes()).decode()for n in ['receipt.json','initial.png','same-live-recapture.png']}}))
'''
out,operation=remote('4090',code,'collect-late-original-native-preflight',timeout=60)
data=json.loads(out);target=HERE/'environment-preflight-completion-01';target.mkdir(exist_ok=False)
for name,raw in data['public_files'].items():
    p=target/name;p.write_bytes(base64.b64decode(raw));assert sha(p)==data['audit']['original_files_SHA'][name]
save(target/'audit.json',data['audit'])
save(target/'collection.json',{'operation':str(operation),'remote_audit_sha256':data['audit_sha256'],
 'local_audit_sha256':sha(target/'audit.json'),'original_operation_timeout_preserved':True})
print(json.dumps({'late_original_preflight_passed':True,'no_model_GUI_scorer_calls':True,'no_retry':True,'local':str(target)}))
