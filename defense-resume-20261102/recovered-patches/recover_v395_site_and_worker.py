"""Restore only the verified owned stopped web container and restart failed startup."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;out=here/'v3.9.5-site-recovery-resume.json';assert not out.exists(),'Inspect existing recovery'
old=json.loads((here/'v3.9.5-vwa-resume.json').read_text());saved=json.loads((here/'v3.9.4-failure-preservation.json').read_text(encoding='utf8'))
code=r'''
import pathlib,json,time,subprocess,hashlib,fcntl,socket,urllib.request,os,shutil
root=pathlib.Path(OLD['root']);release=pathlib.Path(OLD['release']);gate=(root/'v395-site-recovery.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
receipt=root/'v3.9.5-site-recovery-resume.json';assert not receipt.exists()
s=json.loads((root/'status.json').read_text());assert s['phase']=='failed'and s['pid']==OLD['pid']and not pathlib.Path('/proc',str(OLD['pid'])).exists()
error=json.loads((root/'uncaught-failure.json').read_text());assert 'ERR_CONNECTION_REFUSED'in error['traceback']and 'renew_comb'in error['traceback']
preserve=root/'preservation'/('site-startup-'+str(time.time_ns()));preserve.mkdir();hashes={}
for p in [root/'status.json',root/'uncaught-failure.json',pathlib.Path(OLD['log'])]:
 shutil.copy2(p,preserve/p.name);hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
web,db=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds','qwen27_vwa_classifieds_db'],text=True))
for c in [web,db]:
 assert c['Config']['Labels']['owner']=='whz-qwen27-vwa'and c['Config']['Labels']['com.docker.compose.project']=='qwen27_vwa'
assert web['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'
assert web['Image']=='sha256:0dbbdef09dd9ab590b5016b6406cad0bbbfd536647be6644463083c8d5c62617'
assert db['State']['Running']and any(m.get('Name')=='qwen27_vwa_db_data'for m in db['Mounts'])
assert web['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
inspection=[{'id':c['Id'],'name':c['Name'],'state':c['State'],'labels':c['Config']['Labels'],'ports':c['HostConfig']['PortBindings'],'mounts':c['Mounts'],'image':c['Image']}for c in [web,db]]
(preserve/'container-inspection.json').write_text(json.dumps(inspection,indent=2))
logs=subprocess.run(['docker','logs','--tail','100',web['Id']],capture_output=True,text=True);(preserve/'web-before.log').write_text(logs.stdout+logs.stderr)
(preserve/'sha256.json').write_text(json.dumps(hashes,indent=2))
if not web['State']['Running']:
 with socket.socket()as sock:assert sock.connect_ex(('192.0.2.10',29980))!=0
 subprocess.run(['docker','start',web['Id']],check=True,capture_output=True,text=True)
for readiness_attempt in range(10):
 try:
  with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login',timeout=5)as resp:
   html=resp.read();assert resp.status==200 and b'<html'in html.lower();health={'status':resp.status,'bytes':len(html),'sha256':hashlib.sha256(html).hexdigest()}
  break
 except Exception:
  if readiness_attempt==9:raise
  time.sleep(3)
assert hashlib.sha256((root/'uncaught-failure.json').read_bytes()).hexdigest()==hashes[str(root/'uncaught-failure.json')]
for m in SAVED['completed']:
 ptr=json.loads((root/'runs'/m['run_id']/'complete.json').read_text());assert ptr['attempt']==m['attempt']and ptr['sha256']==m['sha256']
 assert hashlib.sha256((pathlib.Path(ptr['attempt'])/'complete.json').read_bytes()).hexdigest()==m['sha256']
assert len(list((root/'runs').glob('*/complete.json')))==10
for n,h in OLD['bindings'].items():assert hashlib.sha256((release/n).read_bytes()).hexdigest()==h
batch=(root/'batch.lock').open('a');fcntl.flock(batch,fcntl.LOCK_EX|fcntl.LOCK_NB)
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.9.5-site-restored-'+str(time.time_ns())+'.log');fcntl.flock(batch,fcntl.LOCK_UN);batch.close()
with log.open('xb')as f:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token'),'--priority-runs',*OLD['priority_runs']],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
result=dict(OLD,pid=p.pid,log=str(log),time=time.time(),startup_failure_preservation=str(preserve),site_recovery={'container_id':web['Id'],'operation':'start existing stopped container','health':health,'database_untouched':True,'no_site_reset':True},superseded_startup_worker=OLD['pid'])
receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
d=json.loads(remote('OLD='+repr(old)+'\nSAVED='+repr(saved)+'\n'+code,host='4090'));out.write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k in ['pid','root','release','log','time','site_recovery','startup_failure_preservation']}))
