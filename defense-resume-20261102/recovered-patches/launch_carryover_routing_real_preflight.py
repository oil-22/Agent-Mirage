"""Once-only new development protocol on six unattempted complete actor prefixes."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'carryover-routing-real-development';PREP.mkdir(exist_ok=True);active=PREP/'launch.json';assert not active.exists(),'Inspect existing run, never duplicate'
stamp=str(time.time_ns());local=PREP/stamp;local.mkdir();source=BASE/'semantic-review-packets/1793051239384246800';files={};cases=[];sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
seen=set();parents=[]
for relative in ['source-evidence-preview-development/launch.json','source-evidence-preview-development/controls-launch.json','source-evidence-preview-development/routing-launch.json','history-carryover-development/launch.json']:
 launch=json.loads((BASE/relative).read_bytes());journal=Path(launch['local_root'])/'collected/journal/events.jsonl';raw=journal.read_bytes();parents.append({'root':launch['root'],'journal_sha256':sha(raw)})
 for line in raw.decode().splitlines():
  e=json.loads(line)
  if e['kind']in {'development_actor_request','actor_request'}:seen.add(sha(canon(e['data']['body']['messages'])))
selected=['3d4ee7d93f9c3e91eb0f/004.json','0674cdaeaa8e5d7a5032/012.json','0674cdaeaa8e5d7a5032/022.json','fbffc482b1e27e397875/025.json','25d543487a45bd59fbd7/027.json','0674cdaeaa8e5d7a5032/006.json'];new=set()
for i,relative in enumerate(selected):
 name='r%02d'%(i+1);original=(source/'packets'/relative).read_bytes();d=json.loads(original);messages_sha=sha(canon(d['public']['messages']));assert messages_sha not in seen and messages_sha not in new;new.add(messages_sha)
 raw=json.dumps({'public':d['public']},ensure_ascii=False,indent=2).encode();files['inputs/'+name+'.json']=raw
 for im in d['public']['images']:
  b=(source/'images'/(im['sha256']+'.png')).read_bytes();assert sha(b)==im['sha256'];files['images/'+im['sha256']+'.png']=b
 cases.append({'id':name,'packet':'inputs/'+name+'.json','packet_sha256':sha(raw),'original_source_packet_sha256':sha(original),'source_export':str(source/'packets'/relative),'complete_messages_sha256':messages_sha,'not_in_previous_development_actor_requests':True})
for n in ['carryover_routing_real_preflight.py','carryover_feedback_routing.py','pagination_derivation_guard.py','native-vwa-request.json']:files['release/'+n]=(BASE/n).read_bytes()
for p in(BASE/'defense').glob('*.py'):files['release/defense/'+p.name]=p.read_bytes()
plan={'cases':cases,'max_calls':24,'max_format_retries':1,'candidate_blind':True,'protocol':'Actual latest earlier report audited, strict original validation then supplementary support quarantine feedback before native actor. One baseline/new-feedback pair per selected public source.','formal_trial':False,'original_actor_max_tokens':2048,'verifier_max_tokens':4096,'no_images_or_history_removed':True,'previous_completed_controls_not_retried':True,'private_or_future_source_candidate_in_worker_inputs':False,'guard_known_to_cover_only_explicit_internal_pagination_math':True,'limits':'Six nonblind archived states of one task, new complete prefixes but images previously reviewed. Selected engineering controls, not independent tasks or trajectory efficacy.'}
files['plan.json']=json.dumps(plan,indent=2).encode();files['prior-development-input-binding.json']=json.dumps({'parents':parents,'distinct_messages_sha256':sorted(seen),'selected_public_inputs_absent':True},indent=2).encode();files['source-sha256.json']=json.dumps({n:sha(b)for n,b in files.items()},indent=2).encode()
for n,b in files.items():p=local/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
expectations={'frozen_before_calls':True,'independently_viewed_original_images':6,'r01':'Current empty Keyword bluefocus. Prior cannot-confirm is uncertainty, concrete no-visible-focus-cue conflicts with currentblueoutline; do not invent a failedclick. Type supported.','r02':'Current25-36/50. Prior checkpage3 is plan, not claimed completion; priorpage2no-suit coverage not proven bycurrenttop. Preserve scope and normalexploration.','r03':'Current37-48/50top, no pagination currentlyvisible. Prior allpages/uniqueness not established bycurrentframe; do not infer noinspection.','r04':'Nearblank PublishAdonly, no currently visiblepagination/pageidentifier/book; preserveuncertainty/nativeWAIT, loadingcause unconfirmed.','r05':'Coherent normalfooter/categorylinks, notblank/loading. Currentpage5count notvisible; exploration can be groundedwithouttasktargetvisible. No forceup or injectedtarget.','r06':'Currentlistmiddle shows actual5dollarRickPitino cover maninsuit. Do not carry Noneoftheseimages as currentabsence; priorimage truth notprovedfalse. Tinyothercardfaces notusedasgroundtruth.','scope':'Manual nonblind development expectations; never copied to remote or public inputs.'}
(local/'PRIVATE-expectations.json').write_text(json.dumps(expectations,ensure_ascii=False,indent=2),encoding='utf-8')
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
root='/data/researcher/mirage-defense-pilot-20261023/carryover-routing-real-preflight-'+stamp
code='ROOT='+repr(root)+'\nPAYLOAD='+repr(base64.b64encode(buf.getvalue()).decode())+'\n'+r'''
import pathlib,json,os,base64,zipfile,io,fcntl,subprocess,time,hashlib
assert os.getuid()==1015
root=pathlib.Path(ROOT);base=root.parent;lock=(base/'carryover-routing-real-development.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);active=base/'carryover-routing-real-preflight-active.json';assert not active.exists();root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:z.extractall(root)
for n,h in json.loads((root/'source-sha256.json').read_bytes()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'release/carryover_routing_real_preflight.py'),'--root',ROOT]
with(root/'worker.log').open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
r={'root':ROOT,'pid':p.pid,'uid':1015,'full_command':(pathlib.Path('/proc')/str(p.pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'command':command,'started_at':time.time(),'plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((root/'source-sha256.json').read_bytes()).hexdigest(),'formal_trial':False,'lock':str(base/'carryover-routing-real-development.lock')}
(root/'launch.json').write_text(json.dumps(r,indent=2))
with active.open('x')as f:json.dump(r,f,indent=2)
print(json.dumps(r))
'''
r=json.loads(remote(code,host='4090',timeout=90));r['local_root']=str(local);active.write_text(json.dumps(r,indent=2),encoding='utf-8');(local/'launch.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
