"""Read-only process/lock/request evidence accompanying the semantic audit."""
import hashlib
import json
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent
OUT=BASE/'heartbeat-evidence/1793111971146570900'
assert OUT.exists() and not (OUT/'ownership-request-evidence.json').exists()
service=json.loads(remote(r'''
import os,pathlib,json,hashlib,pwd,subprocess,time
root=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023/inference-service-v10-1792914231469085180')
p=pathlib.Path('/proc/2140814');assert p.exists()and p.stat().st_uid==1033
cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
assert 'de550b92fd0f6fa6/inference_server.py'in cmd and str(root)in cmd and '--placement balanced'in cmd
lock=root/'service.lock';inode=lock.stat().st_ino
lock_lines=[x for x in pathlib.Path('/proc/locks').read_text().splitlines()if '2140814'in x and str(inode)in x]
assert lock_lines,'Service lock is not verified held by the service PID'
requests=[]
for d in sorted((root/'requests').glob('*'))[-3:]:
 if not d.is_dir():continue
 files={}
 for name in ['request.json','progress.json','response.json','failure.json','generation-progress.json']:
  f=d/name
  if not f.exists():continue
  raw=f.read_bytes();entry={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'age_seconds':time.time()-f.stat().st_mtime}
  try:v=json.loads(raw);entry['metadata']={k:v[k]for k in ['phase','input_tokens','output_tokens','generated_tokens','seconds','error']if k in v}
  except ValueError:pass
  files[name]=entry
 requests.append({'directory':d.name,'files':files})
ss=subprocess.run(['ss','-Htnp','sport', '= :18127'],capture_output=True,text=True,timeout=15)
logs={}
for f in root.glob('*.log'):
 raw=f.read_bytes();logs[f.name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'age_seconds':time.time()-f.stat().st_mtime}
print(json.dumps({'time':time.time(),'uid':p.stat().st_uid,'owner':pwd.getpwuid(p.stat().st_uid).pw_name,'pid':2140814,'full_command':cmd,'service_lock_path':str(lock),'service_lock_inode':inode,'held_lock_lines':lock_lines,'recent_request_response_files':requests,'client_socket_snapshot':{'returncode':ss.returncode,'stdout':ss.stdout,'stderr':ss.stderr},'log_sha256':logs,'read_only':True}))
''',host='3090',timeout=60))
workers=json.loads(remote(r'''
import os,pathlib,json,time,pwd
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=1015:continue
  parts=(p/'cmdline').read_bytes().split(b'\0')
  if b'python3'in parts and b'-'in parts:continue
  cmd=' '.join(x.decode(errors='replace')for x in parts)
  if not any(k in cmd for k in ['run_vwa_pilot.py','run_uitars','uitars-real','run_qwen9','qwen9-remaining','glm-scale']):continue
  rows.append({'pid':int(p.name),'uid':p.stat().st_uid,'full_command':cmd})
 except OSError:pass
print(json.dumps({'time':time.time(),'ssh_uid':os.getuid(),'owner':pwd.getpwuid(os.getuid()).pw_name,'owned_matching_processes':rows,'read_only':True,'note':'Exited completed workers are not faults. No launch/stop or resource allocation.'}))
''',host='4090',timeout=45))
raw=(json.dumps({'service':service,'workers4090':workers},ensure_ascii=False,indent=2)+'\n').encode('utf-8')
(OUT/'ownership-request-evidence.json').write_bytes(raw)
print(json.dumps({'path':str(OUT/'ownership-request-evidence.json'),'sha256':hashlib.sha256(raw).hexdigest(),'service_uid':service['uid'],'service_lock_verified':bool(service['held_lock_lines']),'last_request_count':len(service['recent_request_response_files']),'matching_workers':workers['owned_matching_processes']}))
