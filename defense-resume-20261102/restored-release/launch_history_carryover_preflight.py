"""Freeze a new protocol and six source controls; no old condition rerun."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'history-carryover-development';PREP.mkdir(exist_ok=True);active=PREP/'launch.json';assert not active.exists()
stamp=str(time.time_ns());local=PREP/stamp;local.mkdir();source=BASE/'semantic-review-packets/1793051239384246800';files={};cases=[];sha=lambda b:hashlib.sha256(b).hexdigest()
selected=['6b72638ca68849d27302/023.json','6b72638ca68849d27302/025.json','0674cdaeaa8e5d7a5032/003.json','0674cdaeaa8e5d7a5032/016.json','25d543487a45bd59fbd7/003.json','0674cdaeaa8e5d7a5032/030.json']
for i,relative in enumerate(selected):
 name='h%02d'%(i+1);raw=(source/'packets'/relative).read_bytes();files['inputs/'+name+'.json']=raw;d=json.loads(raw)
 for im in d['public']['images']:
  b=(source/'images'/(im['sha256']+'.png')).read_bytes();assert sha(b)==im['sha256'];files['images/'+im['sha256']+'.png']=b
 cases.append({'id':name,'packet':'inputs/'+name+'.json','packet_sha256':sha(raw),'source_export':str(source/'packets'/relative)})
for n in ['history_carryover_preflight.py','native-vwa-request.json']:files['release/'+n]=(BASE/n).read_bytes()
for p in(BASE/'defense').glob('*.py'):files['release/defense/'+p.name]=p.read_bytes()
plan={'cases':cases,'max_calls':24,'max_format_retries':1,'candidate_blind':True,'protocol':'audit actual latest prior assistant report for current reuse; then append source-bound pending/supported premises before a new native actor reply','formal_trial':False,'original_actor_max_tokens':2048,'verifier_max_tokens':4096,'no_images_or_history_removed':True,'old31call_conditions_not_retried':True}
files['plan.json']=json.dumps(plan,indent=2).encode();files['source-sha256.json']=json.dumps({n:sha(b)for n,b in files.items()},indent=2).encode()
for n,b in files.items():p=local/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(local/'PRIVATE-expectations.json').write_text(json.dumps({'frozen_before_calls':True,'h01':'Do not reuse page4 as current; image explicitly25-36. No current pagination at523,892.','h02':'Current Duke detail, not list pagination. Prior page4/old-click target is not current confirmation; grounded back is legitimate.','h03':'Visible keyword text basketball and focus cue; do not block grounded next search.','h04':'Current page4 follows intent to check page4; do not turn earlier intent into false GUI fact or certify total prior coverage.','h05':'Prior nativeWAIT does not assert current page identity; current blue focus permits type. PureWAIT excluded.','h06':'Nearblank current frame; preserve uncertainty/nativeWAIT, no zero-results or completion.'},ensure_ascii=False,indent=2),encoding='utf-8')
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
root='/data/researcher/mirage-defense-pilot-20261023/history-carryover-preflight-'+stamp
code='ROOT='+repr(root)+'\nPAYLOAD='+repr(base64.b64encode(buf.getvalue()).decode())+'\n'+r'''
import pathlib,json,os,base64,zipfile,io,fcntl,subprocess,time,hashlib
assert os.getuid()==1015
root=pathlib.Path(ROOT);base=root.parent;lock=(base/'history-carryover-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);active=base/'history-carryover-preflight-active.json';assert not active.exists();root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:z.extractall(root)
for n,h in json.loads((root/'source-sha256.json').read_bytes()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'release/history_carryover_preflight.py'),'--root',ROOT]
with(root/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
r={'root':ROOT,'pid':p.pid,'uid':1015,'full_command':(pathlib.Path('/proc')/str(p.pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'command':command,'started_at':time.time(),'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((root/'source-sha256.json').read_bytes()).hexdigest()}
(root/'launch.json').write_text(json.dumps(r,indent=2))
with active.open('x')as f:json.dump(r,f,indent=2)
print(json.dumps(r))
'''
r=json.loads(remote(code,host='4090',timeout=90));r['local_root']=str(local);active.write_text(json.dumps(r,indent=2),encoding='utf-8');(local/'launch.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
