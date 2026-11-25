"""One finite launch dependency job, NOT an hourly monitor or recurring automation."""
import json,msvcrt,time,traceback
from pathlib import Path
from remote import remote
R=Path(__file__).resolve().parent
def save(name,v):
 p=R/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(p)
def get(host,base,name):
 return json.loads(remote(f"import pathlib;p=pathlib.Path({base!r})/{name!r};print(p.read_text()if p.exists()else '{{}}')",host=host))
def dispatch():
 lock=(R/'dispatch.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 stages=json.loads((R/'live-staging.json').read_text());shadow=json.loads((R/'shadow-launch.json').read_text());envlaunch=json.loads((R/'environment-launch.json').read_text())
 env=get('4090',envlaunch['root'],'status.json');assert env['phase']=='environment_preflight_complete'
 assert envlaunch['release']==stages['4090']['release']
 state={'phase':'waiting_shadow_preflight','shadow':shadow,'environment_preflight':envlaunch,'started':time.time(),'scope':'finite VWA20 launch; other60 pilot runs not dispatched'};save('dispatch-status.json',state)
 deadline=time.time()+7200
 while time.time()<deadline:
  current=get('3090',shadow['root'],'status.json')
  state.update(shadow_status=current,updated=time.time());save('dispatch-status.json',state)
  if current['phase']=='preflight_failed':raise RuntimeError('Preflight failed; no online task has been launched')
  if current['phase']=='completed':
   assert current['completed_cases']==20 and current['failed_cases']==0;break
  time.sleep(20)
 else:raise RuntimeError('Preflight dependency timed out; no online task launched')
 # Frozen service launch, exclusive lock and receipt prevent a second model process.
 code='''import pathlib,subprocess,os,json,time
r=pathlib.Path(ROOT);release=pathlib.Path(RELEASE)
lock=r/'service-start.lock';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,str(time.time()).encode());os.close(fd)
root=r/('inference-service-'+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
with(root/'worker.log').open('xb')as out:
 p=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(r/'transport.token'),'--gate-shadow',GATE],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
v=dict(pid=p.pid,root=str(root),release=str(release),time=time.time());(r/'service-launch.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
'''.replace('ROOT',repr(stages['3090']['root'])).replace('RELEASE',repr(stages['3090']['release'])).replace('GATE',repr(shadow['root']+'/status.json'))
 service=json.loads(remote(code));save('service-launch.json',service);state.update(phase='waiting_model_service',service=service);save('dispatch-status.json',state)
 for _ in range(120):
  status=json.loads(remote(f"""import pathlib,json
p=pathlib.Path({service['root']!r});f=p/'status.json';print(f.read_text()if f.exists()else '{{}}')
"""))
  if status.get('phase')=='ready':break
  time.sleep(5)
 else:raise RuntimeError('Inference service did not become ready; online launch remains blocked')
 # Verify the actual cross-server route before the browser worker starts.
 health=remote(f"""import pathlib,urllib.request
token=(pathlib.Path({stages['4090']['root']!r})/'transport.token').read_text().strip()
req=urllib.request.Request('http://192.0.2.11:18127',headers={{'Authorization':'Bearer '+token}})
print(urllib.request.urlopen(req,timeout=15).read().decode())
""",host='4090');assert json.loads(health)['phase']=='ready'
 code='''import pathlib,subprocess,os,json,time
r=pathlib.Path(ROOT);release=pathlib.Path(RELEASE)
lock=r/'vwa-start.lock';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,str(time.time()).encode());os.close(fd)
root=r/('vwa-pilot-'+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
with(root/'worker.log').open('xb')as out:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(r/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
v=dict(pid=p.pid,root=str(root),release=str(release),time=time.time(),expected_runs=20,scope='VWA first phase of plan80; read-only task on isolated27B replica');(root/'formal-start-receipt.json').write_text(json.dumps(v,indent=2));(r/'vwa-launch.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
'''.replace('ROOT',repr(stages['4090']['root'])).replace('RELEASE',repr(stages['4090']['release']))
 live=json.loads(remote(code,host='4090'));save('vwa-launch.json',live);state.update(phase='vwa_dispatched',vwa=live,updated=time.time());save('dispatch-status.json',state)
 for _ in range(360):
  status=get('4090',live['root'],'status.json');state.update(vwa_status=status,updated=time.time());save('dispatch-status.json',state)
  if status.get('phase')=='failed':raise RuntimeError('Native VWA worker failed; evidence preserved')
  if status.get('phase')=='completed'or status.get('step',0)>=1:
   state.update(phase='vwa_running_verified',updated=time.time());save('dispatch-status.json',state);return
  time.sleep(5)
 raise RuntimeError('VWA launched but first executed step has not been verified')
if __name__=='__main__':
 try:dispatch()
 except Exception:
  p=R/'dispatch-status.json';s=json.loads(p.read_text(encoding='utf-8'))if p.exists()else{}
  s.update(phase='failed',traceback=traceback.format_exc(),updated=time.time());save('dispatch-status.json',s);raise
