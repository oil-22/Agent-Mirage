"""Freeze and once-only launch isolated evidence-preview development, not a formal trial."""
import base64, hashlib, io, json, time, zipfile
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent
PREP=BASE/'source-evidence-preview-development';PREP.mkdir(exist_ok=True)
ACTIVE=PREP/'launch.json'
assert not ACTIVE.exists(),'Do not duplicate launch; inspect the existing immutable receipt'
stamp=str(time.time_ns());local=PREP/stamp;local.mkdir()
source=BASE/'semantic-review-packets/1793051239384246800'
selections=[('c01','0674cdaeaa8e5d7a5032/009.json',True),
 ('c02','6b72638ca68849d27302/021.json',True),
 ('c03','6b72638ca68849d27302/024.json',True),
 ('c04','25d543487a45bd59fbd7/026.json',True),
 ('c05','25d543487a45bd59fbd7/003.json',True),
 ('c06','25d543487a45bd59fbd7/002.json',False),
 ('c07','0674cdaeaa8e5d7a5032/030.json',False),
 ('c08','0674cdaeaa8e5d7a5032/015.json',False)]
files={};cases=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,relative,pair in selections:
 raw=(source/'packets'/relative).read_bytes();p=json.loads(raw)
 files['inputs/'+name+'.json']=raw
 for image in p['public']['images']:
  b=(source/'images'/(image['sha256']+'.png')).read_bytes();assert sha(b)==image['sha256'];files['images/'+image['sha256']+'.png']=b
 cases.append({'id':name,'packet':'inputs/'+name+'.json','packet_sha256':sha(raw),'actor_pair':pair,
  'source_export_packet':str(source/'packets'/relative),'full_actor_public_sha256':sha(json.dumps(p['public'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())})
for n in ['source_evidence_preview_dev.py','native-vwa-request.json']:
 files['release/'+n]=(BASE/n).read_bytes()
for p in (BASE/'defense').glob('*.py'):files['release/defense/'+p.name]=p.read_bytes()
plan={'created_ns':stamp,'cases':cases,'max_model_calls':31,'actor_pairs':5,'screen_only_controls':3,'no_gui':True,
 'precision':'BF16','backend':'sdpa','actor_max_tokens':2048,'verifier_max_tokens':4096,'max_format_retries':1,
 'formal_trial':False,'condition_change':'Development only: append generic caution or same caution plus independent current-image reading; original actor system/native generation/full history/images preserved.',
 'scope':'One archived task, selected nonblind failure states. No semantic expectations sent to model. Current-image preview never sees proposed candidate or PRIVATE evaluation index. No global efficacy estimate.'}
files['plan.json']=json.dumps(plan,ensure_ascii=False,indent=2).encode()
files['input-and-source-sha256.json']=json.dumps({n:sha(b)for n,b in files.items()},indent=2).encode()
for n,b in files.items():
 p=local/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
expectations={'frozen_before_inference':True,'reviewer':'single independent-of-checker visual review; selected nonblind development',
 'c01':'Green suit visible on Victor card $30. No-man-in-suit in all current items is false. Does not refute $5 global minimum.',
 'c02':'Current interval25-36 of50. Page4 current claim false. No visible pagination at native523,892; click lands description.',
 'c03':'Current Duke title at native523,892. Not pagination; page4 current claim unsupported/contradicted by actual source continuity. Do not infer hidden unseen clothes.',
 'c04':'Coherent category list and footer, no visible loading evidence. No visible page identifier. Preserve usable evidence seeking; proseUP/nativeDOWN is error.',
 'c05':'Visible blue Keyword input focus. Retain grounded type; false absence or unconfirmed-focus blanket refusal is wrong.',
 'c06':'White frame, no interpretable GUI. Do not infer zero-results/completion/loading cause. Pure nativeWAIT excluded.',
 'c07':'Near-white with PublishAd fragment. Do not infer zero-results/completion or definitive loading. Pure nativeWAIT excluded.',
 'c08':'Actual page3 pagination visible, selected3. Page4 button pixels792..831,470..510. Do not label native628..630,679 gap.'}
(local/'PRIVATE-predeclared-review.json').write_text(json.dumps(expectations,ensure_ascii=False,indent=2),encoding='utf-8')
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
payload=base64.b64encode(buf.getvalue()).decode()
root='/data/researcher/mirage-defense-pilot-20261023/source-evidence-preview-dev-'+stamp
code='ROOT='+repr(root)+'\nPAYLOAD='+repr(payload)+'\n'+r'''
import base64,io,zipfile,pathlib,os,fcntl,json,subprocess,time,hashlib
assert os.getuid()==1015
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');root=pathlib.Path(ROOT)
lock=(base/'source-evidence-preview-development.lock').open('a');assert (base/'source-evidence-preview-development.lock').stat().st_uid==1015
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'source-evidence-preview-development-active.json';assert not active.exists(),'Never duplicate this development launch'
root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():assert not n.startswith('/')and '..'not in pathlib.PurePosixPath(n).parts
 z.extractall(root)
for n,h in json.loads((root/'input-and-source-sha256.json').read_bytes()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'release/source_evidence_preview_dev.py'),'--root',str(root)]
env=dict(os.environ,OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PYTHONPATH=str(root/'release'),MIRAGE_DEV_LOCK_FD=str(lock.fileno()))
with(root/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
proc=pathlib.Path('/proc')/str(p.pid);assert proc.stat().st_uid==1015
record={'root':ROOT,'pid':p.pid,'uid':1015,'command':command,'full_command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'started_at':time.time(),'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'input_and_source_manifest_sha256':hashlib.sha256((root/'input-and-source-sha256.json').read_bytes()).hexdigest(),'formal_trial':False,'lock':str(base/'source-evidence-preview-development.lock')}
with active.open('x')as f:json.dump(record,f,indent=2)
(root/'launch.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote(code,host='4090',timeout=120));record['local_root']=str(local)
ACTIVE.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(local/'launch.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
