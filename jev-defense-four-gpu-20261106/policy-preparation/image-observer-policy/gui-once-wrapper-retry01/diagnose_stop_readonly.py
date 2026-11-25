"""Read actual exited/live identities and raw stop failure, never process control."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
helper=(ROOT/'progress-preparation/progress_remote.py').read_text(encoding='utf8')
tail=r'''
group=Path('/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243')
value=service_snapshot(group)
artifacts={}
for name in('launcher-failure.json','exit.json','stop-requested.json','terminal-sha256.json',
    'primary/stopped.json','pplx_flash/stopped.json','primary.log','pplx_flash.log',
    'process.json','primary-launch.json','pplx_flash-launch.json','runtime-config.json'):
    p=group/name
    if p.exists():
        raw=p.read_bytes();artifacts[name]={'sha256':sha(p),'data':base64.b64encode(raw).decode()}
    else:artifacts[name]={'missing':True}
print(json.dumps({'snapshot':value,'artifacts':artifacts,'time':time.time(),'new_HTTP_model_GUI_signals':0}))
'''
code="import base64\n__name__='audit_helpers'\n"+helper+'\n'+tail
run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','3090',
    '/opt/whz/conda-envs/webmall-vlm/bin/python -B -'],input=code,capture_output=True,text=True,timeout=120)
out=ROOT/('service-stop-diagnostic-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stderr.txt').write_text(run.stderr,encoding='utf8')
if run.returncode:
    (out/'stdout.failure.txt').write_text(run.stdout,encoding='utf8');raise SystemExit(run.returncode)
data=json.loads(run.stdout);missing=[]
for name,item in data['artifacts'].items():
    if item.get('missing'):missing.append(name);continue
    path=out/'originals'/name;path.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];path.write_bytes(raw)
receipt={'snapshot':data['snapshot'],'time':data['time'],'new_HTTP_model_GUI_signals':0,
    'missing_originals':missing,'original_sha256':{n:i['sha256']for n,i in data['artifacts'].items()if'sha256'in i},
    'diagnostic_source_sha256':hashlib.sha256(code.encode()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'source.py').write_text(code,encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
s=data['snapshot'];failure=json.loads((out/'originals/launcher-failure.json').read_bytes())if(out/'originals/launcher-failure.json').exists()else None
print(json.dumps({'local':str(out),'receipt_sha256':hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest(),
    'workers':{role:{'identity_matches':r['identity_matches'],'phase':r['phase'],'actual':r.get('actual'),
    'held_locks':len(r.get('actual_locks',[])),'request_counts':r['request_counts']}for role,r in s['workers'].items()},
    'launcher':s['launcher'],'holder':{'identity_matches':s['holder']['identity_matches'],
    'held_locks':len(s['holder'].get('actual_locks',[]))},'GPU4_7':s['physical_GPU4_7'],'target_compute':s['target_compute'],
    'missing_originals':missing,'launcher_failure':failure,'new_HTTP_model_GUI_signals':0}))
