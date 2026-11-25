"""User-authorized pause, preserving requests/logs and checking actual owned identity."""
import hashlib
import json
import sys
import time
from pathlib import Path
from remote import remote

CODE = r'''
import pathlib,os,json,time,hashlib,shutil,subprocess,signal
assert os.getuid()==1033
service=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023/inference-service-v10-1792914231469085180')
pid=2140814;proc=pathlib.Path('/proc')/str(pid)
cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert proc.stat().st_uid==1033 and 'de550b92fd0f6fa6/inference_server.py'in cmd and str(service)in cmd
start=(proc/'stat').read_text().split()[21]
locks=[l for l in pathlib.Path('/proc/locks').read_text().splitlines()if str(pid)in l and str((service/'service.lock').stat().st_ino)in l];assert locks
clients=subprocess.check_output(['ss','-Htnp','state','established','sport','= :18127'],text=True);assert not clients.strip()
root=service.parent/('user-paused-for-qwen27-'+str(time.time_ns()));root.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=[]
for old in sorted(service.parent.glob('user-paused-for-qwen27-*')):
 if old==root:continue
 previous.append({'root':str(old),'files':{str(p.relative_to(old)):sha(p)for p in old.rglob('*')if p.is_file()},'known_failure':'os.pidfd_open unavailable; no signal was sent'})
(root/'previous-stop-preparation-failure.json').write_text(json.dumps(previous,indent=2))
for name in ['runtime.json','status.json','worker.log']:
 if(service/name).exists():shutil.copy2(service/name,root/('before-'+name))
recent=[]
for d in sorted((service/'requests').iterdir())[-5:]:
 if d.is_dir():
  assert (d/'response.json').exists()or(d/'failure.json').exists(),d.name
  shutil.copytree(d,root/'requests'/d.name);recent.append(d.name)
record={'user_instruction':'把防御先停下来，做27b的可解释性','time':time.time(),'uid':1033,'pid':pid,'full_command':cmd,'process_start_ticks':start,'held_lock_lines':locks,'established_clients':clients,'recent_request_directories':recent,'service_root':str(service),'restart_requires_user_resume':True}
(root/'before-stop.json').write_text(json.dumps(record,indent=2))
# The installed Python/kernel exposes no pidfd. Recheck UID, full command and
# process start time immediately before signalling this one verified service.
assert proc.stat().st_uid==1033 and (proc/'stat').read_text().split()[21]==start
assert (proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()==cmd
os.kill(pid,signal.SIGTERM)
for i in range(100):
 if not proc.exists():break
 time.sleep(.1)
assert not proc.exists(),'Service did not exit after SIGTERM'
for name in ['runtime.json','status.json','worker.log']:
 if(service/name).exists():shutil.copy2(service/name,root/('after-'+name))
record.update(stopped_at=time.time(),service_process_gone=True,site_database_left_intact=True)
(root/'stop-result.json').write_text(json.dumps(record,indent=2))
manifest={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()};(root/'preservation-sha256.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'preservation_root':str(root),'preservation_manifest_sha256':sha(root/'preservation-sha256.json'),'files':len(manifest),'service_stopped':True,'uid':1033,'pid':pid,'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True),'compute':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)}))
'''

if __name__ == '__main__':
    outer = ('import subprocess\np=subprocess.run(' +
             repr(['/opt/whz/conda-envs/webmall-vlm/bin/python', '-c', CODE]) +
             ',capture_output=True,text=True,timeout=50)\nassert p.returncode==0,p.stderr\nprint(p.stdout)\n')
    result = json.loads(remote(outer, host='3090', timeout=60))
    base = Path(__file__).resolve().parent
    out = base / ('defense-user-paused-' + str(time.time_ns()) + '.json')
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    record = {'snapshot': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
              'defense_paused_by_user': True, 'do_not_restart_service_or_defense_workers': True,
              'priority': 'original27B interpretability', **result}
    (base / 'defense-user-pause-current.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record))
