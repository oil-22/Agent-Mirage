"""Gate a source-initialized live diagnostic; no formal reruns before review."""
import base64,hashlib,json
from pathlib import Path
from remote import remote

r=Path(__file__).resolve().parent;out=r/'v3.9.7-live-launch.json';assert not out.exists()
dev=json.loads((r/'v3.9.7-staging-retry.json').read_bytes());saved=json.loads((r/'v3.9.7-scroll-failure-preservation.json').read_bytes())
names=['scroll_live_recovery.py','run_vwa_pilot.py'];files={n:base64.b64encode((r/n).read_bytes()).decode()for n in names};identity=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
code=r'''
import pathlib,json,hashlib,shutil,subprocess,os,time,base64,ast
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');prior=pathlib.Path(DEV['release']);release=prior.parent/IDENTITY;assert not release.exists()
shutil.copytree(prior,release,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name,b64 in FILES.items():(release/name).write_bytes(base64.b64decode(b64))
assert (release/'defense/core.py').read_bytes()==(prior/'defense/core.py').read_bytes()
# Run selection adds CLI bookkeeping only. All native callbacks and step loop exact.
b=ast.parse((prior/'run_vwa_pilot.py').read_text());a=ast.parse((release/'run_vwa_pilot.py').read_text())
bf={n.name:ast.dump(n,include_attributes=False)for n in ast.walk(b)if isinstance(n,ast.FunctionDef)and n.name!='main'}
af={n.name:ast.dump(n,include_attributes=False)for n in ast.walk(a)if isinstance(n,ast.FunctionDef)and n.name!='main'}
assert bf==af
bs=next(n for n in ast.walk(b)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='step')
as_=next(n for n in ast.walk(a)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='step')
assert ast.dump(bs,include_attributes=False)==ast.dump(as_,include_attributes=False)
for n in ['plan80.json','native-vwa-request.json','defense/schema.py','defense/prompts.py','defense/http_backend.py','defense/qwen_backend.py']:assert(release/n).read_bytes()==(prior/n).read_bytes()
env=dict(os.environ,DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
root=base/('scroll-live-recovery-'+str(time.time_ns()));log=root.with_suffix('.log')
source=next(x['source']for x in SAVED['rows']if x['arm']=='joint')
command=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'scroll_live_recovery.py'),'--source',source,'--root',str(root),'--development',DEV['root'],'--token-file',str(base/'transport.token')]
with log.open('xb')as stream:p=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
record={'time':time.time(),'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'command':command,'development_root':DEV['root'],'source':source,'core_sha256':hashlib.sha256((release/'defense/core.py').read_bytes()).hexdigest(),'run_selection_only_added_to_runner':True,'source_original_results_untouched':True}
(base/'scroll-live-recovery-active.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
'''
record=json.loads(remote('DEV='+repr(dev)+'\nSAVED='+repr(saved)+'\nFILES='+repr(files)+'\nIDENTITY='+repr(identity)+'\n'+code,host='4090',timeout=50))
out.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record))
