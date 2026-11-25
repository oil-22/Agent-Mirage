import base64,json,hashlib
from pathlib import Path
from remote import remote
R=Path(__file__).resolve().parent
files={name:base64.b64encode((R/name).read_bytes()).decode()for name in ['defense/__init__.py','defense/core.py','defense/prompts.py','defense/qwen_backend.py','run_shadow.py','shadow-manifest.json']}
release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code='''import pathlib,json,base64,subprocess,os,time,py_compile
p=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023')
release=p/'releases'/RELEASE
release.mkdir(parents=True,exist_ok=True)
files=json.loads(PAYLOAD)
for name,data in files.items():
 out=release/name;out.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(data)
 if out.exists():assert out.read_bytes()==raw,name
 else:out.write_bytes(raw)
for name in files:
 if name.endswith('.py'):py_compile.compile(str(release/name),doraise=True)
manifest=json.loads((release/'shadow-manifest.json').read_text())
source=pathlib.Path('/home/researcher/qwen27-attention-pilot-20261020/inputs/cases')
for case in manifest['cases']:
 dest=p/'shadow-inputs'/case['task'];dest.mkdir(parents=True,exist_ok=True)
 for output,name in [('request.json',f"{case['step']:03}.json"),('response.json',f"{case['step']:03}-response.json")]:
  raw=(source/case['task']/'requests'/name).read_bytes();out=dest/output
  if out.exists():assert out.read_bytes()==raw
  else:out.write_bytes(raw)
(p/'shadow-inputs/shadow-manifest.json').write_text(json.dumps(manifest,indent=2))
for gpu in range(4):
 used=int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip());assert used<1024,(gpu,used)
if (p/'shadow-launch.json').exists():
 old=json.loads((p/'shadow-launch.json').read_text());proc=pathlib.Path('/proc')/str(old['pid'])
 assert not proc.exists() or proc.joinpath('stat').read_text().split()[2]=='Z','Existing worker is active'
root=p/('shadow-preflight-'+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0,1,2,3',HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
log=root/'worker.log'
with log.open('xb')as out:
 child=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'run_shadow.py'),'--inputs',str(p/'shadow-inputs'),'--root',str(root),'--limit','20'],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=child.pid,root=str(root),release=str(release),log=str(log),time=time.time(),scope='20 real verifier preflight cases; no GUI actions; stops at first failure')
(root/'launch.json').write_text(json.dumps(receipt,indent=2));(p/'shadow-launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
'''.replace('PAYLOAD',repr(json.dumps(files))).replace('RELEASE',repr(release))
out=remote(code);(R/'shadow-launch.json').write_text(out);print(out)
