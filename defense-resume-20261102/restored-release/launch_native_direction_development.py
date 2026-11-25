"""Once-only launch of four NEW archived-prefix controls; no GUI/old queues."""
import base64
import argparse
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--linked-startup-retry',action='store_true');args=ap.parse_args()
    stage=json.loads((BASE/'native-direction-development/current.json').read_bytes())
    local=Path(stage['directory']);manifest=json.loads((local/'source-sha256.json').read_bytes())
    launchname='launch-startup-retry.json' if args.linked_startup_retry else 'launch.json'
    assert not(local/launchname).exists()
    retry=json.loads((BASE/'native-direction-development/worker-startup-failure-current.json').read_bytes())if args.linked_startup_retry else None
    assert json.loads((local/'cpu-tests.json').read_bytes())['returncode']==0
    assert not any('PRIVATE' in n or 'offline' in n for n in manifest)
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED)as z:
        for n,h in manifest.items():
            raw=(local/n).read_bytes();assert hashlib.sha256(raw).hexdigest()==h,n;z.writestr(n.replace('\\','/'),raw)
        z.writestr('source-sha256-windows.json',(local/'source-sha256.json').read_bytes())
        portable={n.replace('\\','/'):h for n,h in manifest.items()}
        assert len(portable)==len(manifest)
        z.writestr('source-sha256.json',json.dumps(portable,indent=2))
    root='/data/researcher/mirage-defense-pilot-20261023/native-direction-real-preflight-'+str(time.time_ns())
    code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
base=Path('/data/researcher/mirage-defense-pilot-20261023')
lock=(base/'native-direction-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'native-direction-development-active-20261028.json'
if RETRY:
 previous=json.loads(active.read_bytes());assert all(previous[k]==RETRY['failed_launch'][k]for k in previous)
 assert not(Path('/proc')/str(previous['pid'])).exists()
 failed=Path(previous['root']);assert not(failed/'status.json').exists()and not(failed/'journal').exists()
 assert "KeyError: 'DATASET'" in(failed/'worker.log').read_text()
 active=base/'native-direction-development-startup-retry-active-20261028.json'
assert not active.exists(),'Once-only receipt exists: inspect, do not launch again'
root=Path(ROOT);assert not root.exists();root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for n in z.namelist():
  p=(root/n).resolve();p.relative_to(root.resolve());assert 'PRIVATE'not in n
 z.extractall(root)
manifest=json.loads((root/'source-sha256.json').read_bytes())
for n,h in manifest.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
py='/data/researcher/vwa100-2026-10-09/venv/bin/python'
tests=subprocess.run([py,str(root/'release/test_native_direction_development.py')],cwd=root/'release',capture_output=True,text=True,timeout=60)
(root/'remote-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
command=[py,'-u',str(root/'release/run_native_direction_development.py'),'--root',str(root)]
row={'root':str(root),'phase':'reserved_before_spawn','time':time.time(),'uid':1015,'max_calls':24,'formal_trial':False,'old_queues_resumed':False,'private_expectations_transferred':False,'development_service':SERVICE,'linked_startup_failure':FAILURE}
with active.open('x')as f:json.dump(row,f,indent=2)
env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',CUDA_VISIBLE_DEVICES='',DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset')
nativecheck=subprocess.run([py,'-c',"from run_reddit_internvl_smoke import parse,action; assert action(parse('<action>{\"type\":\"scroll\",\"direction\":\"up\"}</action>'))"],cwd='/data/researcher/vwa100-2026-10-09',env=env,capture_output=True,text=True,timeout=60)
(root/'native-import-preflight.json').write_text(json.dumps({'returncode':nativecheck.returncode,'stdout':nativecheck.stdout,'stderr':nativecheck.stderr},indent=2));assert nativecheck.returncode==0,nativecheck.stderr
row['linked_worker_startup_failure']=RETRY
with(root/'worker.log').open('xb')as log:
 p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
row.update(phase='launched',pid=p.pid,command=command)
(root/'launch.json').write_text(json.dumps(row,indent=2));tmp=active.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2));tmp.replace(active)
print(json.dumps(row))
'''
    service=json.loads((BASE/'defense-service-resume-current.json').read_bytes())
    failure=json.loads((BASE/'native-direction-development/startup-failure-current.json').read_bytes())
    row=json.loads(remote('ROOT='+repr(root)+'\nRETRY='+repr(retry)+'\nARCHIVE='+repr(base64.b64encode(data.getvalue()).decode())+'\nFAILURE='+repr(failure)+'\nSERVICE='+repr({'root':service['root'],'gpus':service['gpus'],'release':service['release'],'formal_trial':False})+'\n'+code,host='4090',timeout=100))
    (local/launchname).write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'native-direction-development/launch-current.json').write_text(json.dumps({'local':str(local),**row},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row))
