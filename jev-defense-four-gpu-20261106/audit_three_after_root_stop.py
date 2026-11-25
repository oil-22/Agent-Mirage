"""Read-only postexit audit after root's marker-only stop; no signals."""
import base64,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE=Path(__file__).resolve().parent
CODE=r'''
import base64,hashlib,json,os,subprocess,time
from pathlib import Path
B=Path('/home/researcher/jev-defense-four-gpu-20261106');g=B/'online-three-service-group-1793985778592347799'
pre=B/'three-terminal-prestop-preservation/1794040105015962100'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  while True:
   x=f.read(4194304)
   if not x:break
   h.update(x)
 return h.hexdigest()
def save(p,x):
 with p.open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2)
 os.chmod(str(p),0o600)
assert sha(pre/'receipt.json')=='16fb3e744dcf373932a3ba44c4fc690284049f150e95505816a974758e6be386'
assert sha(g/'stop-requested.json')=='1348a91af818de7cc4406ae866738a6836226203a622700dfd1a09265940ff46'
terminal=json.loads((g/'terminal-sha256.json').read_bytes());exitdata=json.loads((g/'exit.json').read_bytes())
bad=[n for n,h in terminal.items()if sha(g/n)!=h]
assert not bad,('actual_terminal_manifest_mismatch',bad)
before=json.loads((pre/'source-manifests-before.json').read_bytes())
changed=[];missing=[]
for n,h in before['service-group'].items():
 p=g/n
 if not p.exists():missing.append(n)
 elif 'sha256'in h and sha(p)!=h['sha256']:changed.append(n)
reqchanged=[n for n in changed+missing if '/requests/'in n or n.startswith('transitions/')]
assert not reqchanged,('original_request_or_transition_changed',reqchanged)
assert not missing,missing
source_bindings={}
for name,path in [('online-source',B/'runtime-preparation/gui-three-linked02-1793985778592347799'),
 ('primary-release',B/'primary-release-01'),('preflight-source',B/'runtime-preparation/failed-layout-capacity-1793984469336572715')]:
 for n,h in before[name].items():
  if'sha256'in h:assert sha(path/n)==h['sha256'],(name,n)
 source_bindings[name]={'files':len(before[name]),'all_original_SHA_equal':True}
ids={r['role']:r['identity']for r in exitdata['workers']}
ids['launcher']=json.loads((g/'process.json').read_bytes())
proc={name:{'pid':r['pid'],'proc_path_exists':Path('/proc',str(r['pid'])).exists()}for name,r in ids.items()}
assert not any(r['proc_path_exists']for r in proc.values()),proc
lease=json.loads((B/'resource-attempt-20261106-01/lease.json').read_bytes());holder=lease['holder'];p=Path('/proc',str(holder['pid']))
stattext=(p/'stat').read_text();tail=stattext[stattext.rfind(')')+2:].split()
actual={'pid':holder['pid'],'uid':p.stat().st_uid,'start_ticks':tail[19],
 'command':(p/'cmdline').read_bytes().rstrip(b'\0').replace(b'\0',b' ').decode()}
assert all(str(actual[k])==str(holder[k])for k in actual)
locks=[]
for e in lease['lock_records']:
 fd=p/'fd'/str(e['fd']);fi=p/'fdinfo'/str(e['fd'])
 assert str(fd.readlink())==e['path']and fd.stat().st_ino==e['inode']and'lock:'in fi.read_text()
 locks.append({'fd':e['fd'],'path':e['path'],'inode':e['inode']})
uuids={r['uuid']for r in lease['gpu']};compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']).decode().splitlines():
 if line.strip():
  u,pid=line.split(',')
  if u.strip()in uuids:compute.append({'uuid':u.strip(),'pid':int(pid.strip())})
assert not compute,compute
stopdata={role:json.loads((g/role/'stopped.json').read_bytes())for role in('primary','pplx_flash')}
codes={r['role']:r['exit_code']for r in exitdata['workers']}
root=B/'three-terminal-postexit-audit'/str(time.time_ns());root.mkdir(mode=0o700,parents=True,exist_ok=False)
public=['exit.json','terminal-sha256.json','stop-requested.json','primary/stopped.json','pplx_flash/stopped.json']
for name in public:
 p=root/'public'/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 with p.open('xb')as f:f.write((g/name).read_bytes())
 os.chmod(str(p),0o600)
report={'status':'postexit_audit_passed'if all(v==0 for v in codes.values())else'postexit_exit_codes_nonzero',
 'group':str(g),'time':time.time(),'prestop_receipt_sha256':sha(pre/'receipt.json'),
 'root_stop_marker_sha256':sha(g/'stop-requested.json'),'actual_original_exit_codes':codes,
 'original_exit_json_sha256':sha(g/'exit.json'),'original_terminal_manifest_sha256':sha(g/'terminal-sha256.json'),
 'all_actual_terminal_manifest_entries_verified':len(terminal),'original_request_and_transition_files_unchanged':True,
 'changed_pre_stop_files':changed,'missing_pre_stop_files':missing,'all_original_runtime_sources_unchanged':source_bindings,
 'actual_workers_and_launcher_absent':proc,'target_GPU_compute_empty':True,'holder':actual,'holder_actual_locks':locks,
 'no_manifest_or_exit_fabricated':True,'new_model_GUI_health_scorer_stop_signal_or_marker_writes':0,
 'prestop_all_source_request_pixels_history_already_preserved':True}
save(root/'report.json',report)
mapping={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()};save(root/'seal.json',mapping)
names=list(mapping)+['seal.json']
print(json.dumps({'root':str(root),'report_sha256':sha(root/'report.json'),'seal_sha256':sha(root/'seal.json'),
 'brief':{k:report[k]for k in('status','actual_original_exit_codes','original_terminal_manifest_sha256','all_actual_terminal_manifest_entries_verified','changed_pre_stop_files','target_GPU_compute_empty')},
 'public_files':{n:{'base64':base64.b64encode((root/n).read_bytes()).decode(),'sha256':sha(root/n)}for n in names}}))
'''
if __name__=='__main__':
 out=BASE/'three-terminal-postexit-public'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
 try:
  value=json.loads(remote(CODE,timeout=180,host='3090'))
  for n,row in value.pop('public_files').items():
   raw=base64.b64decode(row['base64']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
   p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb')as f:f.write(raw)
  (out/'transfer.json').write_text(json.dumps(value,indent=2),encoding='utf8')
  print(json.dumps({'local_root':str(out),**value}))
 finally:(out/'local-transfer-seal.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
