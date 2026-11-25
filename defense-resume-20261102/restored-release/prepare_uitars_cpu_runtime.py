"""Copy the exact active verifier grammar into an isolated CPU-only candidate preflight."""
import argparse,base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('--extension',action='store_true');ap.add_argument('--retry-origin');args=ap.parse_args()
base=Path(__file__).resolve().parent;prep=base/'uitars-verifier-preparation';receipt=prep/('cpu-extension-retry-launch.json'if args.retry_origin else'cpu-extension-launch.json'if args.extension else'cpu-preflight-launch.json')
if args.retry_origin:
 assert args.extension
 saved=json.loads((prep/'cpu-extension-failure-preservation.json').read_bytes());assert saved['root']==args.retry_origin
if args.extension:
 prior=json.loads((prep/'cpu-preflight-current.json').read_bytes());assert prior['completed']
 assert json.loads((prep/'frozen-controls-current.json').read_bytes())['cases']==20
assert not receipt.exists(),'Inspect existing CPU preflight first'
identity=json.loads(Path(json.loads((prep/'identity-current.json').read_bytes())['path']).read_bytes())
assert all(v['manifest_match']for v in identity['weights'])
upstream=json.loads((prep/'pinned-upstream-api-20261027.json').read_bytes())
assert upstream['sha']==identity['manifest']['revision']
siblings={v['rfilename']:v for v in upstream['siblings']}
for w in identity['weights']:assert siblings[w['file']]['lfs']['sha256']==w['actual_sha256']
dep=json.loads(remote(r'''
import pathlib,hashlib,zipfile,io,base64,json
r=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023/repair-deps-v2');buf=io.BytesIO();sha={}
with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED)as z:
 for p in sorted(r.rglob('*')):
  if not p.is_file()or'__pycache__'in p.parts:continue
  raw=p.read_bytes();name=str(p.relative_to(r));z.writestr(name,raw);sha[name]=hashlib.sha256(raw).hexdigest()
print(json.dumps({'source':str(r),'sha256':sha,'zip_base64':base64.b64encode(buf.getvalue()).decode()}))
''',host='3090',timeout=45))
depbytes=base64.b64decode(dep.pop('zip_base64'));(prep/'active27b-grammar-deps.zip').write_bytes(depbytes)
(prep/'active27b-grammar-deps-source.json').write_text(json.dumps(dep,indent=2),encoding='utf8')
frozen=Path(json.loads((prep/'frozen-controls-current.json').read_bytes())['folder']);bundle=io.BytesIO();sha={}
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_STORED)as z:
 for p in sorted(frozen.iterdir()):
  if p.name.startswith('PRIVATE-')or p.name=='manifest.json':continue
  raw=p.read_bytes();z.writestr(p.name,raw);sha[p.name]=hashlib.sha256(raw).hexdigest()
 for p in [base/'uitars_cpu_preflight.py',*(base/'defense').glob('*.py')]:
  name='release/'+('defense/'+p.name if p.parent.name=='defense'else p.name);raw=p.read_bytes();z.writestr(name,raw);sha[name]=hashlib.sha256(raw).hexdigest()
with zipfile.ZipFile(io.BytesIO(depbytes))as z:
 with zipfile.ZipFile(bundle,'a',zipfile.ZIP_STORED)as b:
  for n in z.namelist():raw=z.read(n);b.writestr('deps/'+n,raw);sha['deps/'+n]=hashlib.sha256(raw).hexdigest()
payload=base64.b64encode(bundle.getvalue()).decode();(prep/'cpu-preflight-bundle.zip').write_bytes(bundle.getvalue())
code=r'''
import pathlib,json,hashlib,base64,io,zipfile,os,time,subprocess,fcntl
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');gate=(base/'uitars-cpu-preparation.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/ACTIVE;assert not active.exists(),'Inspect prior CPU preflight'
if RETRY:
 old=pathlib.Path(RETRY);assert(old/'cpu-failure-preservation.json').exists()and not(old/'cpu-result.json').exists()
assert os.getuid()==1015
root=base/(PREFIX+str(time.time_ns()));root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for name in z.namelist():
  target=root/name;assert os.path.commonpath([str(target.resolve()),str(root.resolve())])==str(root.resolve())
  raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==SHAS[name]
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
model=pathlib.Path('/data/llms/UI-TARS-1.5-7B');upstream_metadata=[]
for s in UPSTREAM['siblings']:
 p=model/s['rfilename']
 if not p.exists()or p.suffix not in ['.json','.txt']:continue
 raw=p.read_bytes();lfs=s.get('lfs')
 actual=hashlib.sha256(raw).hexdigest()if lfs else hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 expected=lfs['sha256']if lfs else s['blobId']
 upstream_metadata.append({'file':p.name,'hash_kind':'lfs_sha256'if lfs else'git_blob_sha1','actual':actual,'upstream':expected,'match':actual==expected})
(root/'pinned-metadata-audit.json').write_text(json.dumps(upstream_metadata,indent=2))
assert all(v['match']for v in upstream_metadata),upstream_metadata
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(root/'deps')+':'+str(root/'release'))
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'release/uitars_cpu_preflight.py'),'--root',str(root)]
log=root/'cpu.log'
with log.open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
record={'time':time.time(),'pid':p.pid,'uid':os.getuid(),'root':str(root),'command':command,'log':str(log),'code_and_input_sha256':SHAS,'pinned_revision':UPSTREAM['sha'],'pinned_metadata':upstream_metadata,'gpu_allocation':False,'model_inference':False,'formal_ready':False,'retry_origin':RETRY}
with active.open('x')as f:json.dump(record,f,indent=2)
(root/'launch.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
mode_vars='ACTIVE='+repr('uitars-cpu-extension-retry-active.json'if args.retry_origin else'uitars-cpu-extension-active.json'if args.extension else'uitars-cpu-preflight-active.json')+'\nPREFIX='+repr('uitars-cpu-extension-retry-'if args.retry_origin else'uitars-cpu-extension-'if args.extension else'uitars-cpu-preflight-')+'\nRETRY='+repr(args.retry_origin)+'\n'
record=json.loads(remote(mode_vars+'PAYLOAD='+repr(payload)+'\nSHAS='+repr(sha)+'\nUPSTREAM='+repr(upstream)+'\n'+code,host='4090',timeout=60))
record['full_weights_verified_against_pinned_official_lfs']=True;record['local_full_weight_identity']=str(prep/'identity-current.json')
receipt.write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items()if k!='code_and_input_sha256'}))
