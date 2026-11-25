"""Start serial new-path checks, keeping the failed v3.5 controls immutable."""
import json,argparse
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--version',choices=['v3.6','v3.6.1','v3.6.2'],default='v3.6');a=ap.parse_args()
receipt=r/(a.version+'-probe-launch.json');assert not receipt.exists()
old=json.loads((r/'v3.5-comparison-launch.json').read_text());negative=json.loads((r/'v3.5-negative-launch.json').read_text())
stage=json.loads((r/'v2-staging.json').read_text())
prior_name={'v3.6.1':'v3.6','v3.6.2':'v3.6.1'}.get(a.version)
prior_probe=json.loads((r/(prior_name+'-probe-launch.json')).read_text())if prior_name else None
pids=[old['pid'],negative['pid']]+([prior_probe['pid']]if prior_probe else[])
code=r'''
import pathlib,json,hashlib,subprocess,time,ast
old=pathlib.Path(OLD);negative=pathlib.Path(NEGATIVE);release=pathlib.Path(RELEASE);prior=pathlib.Path(PRIOR)
for pid in PIDS:assert not pathlib.Path('/proc/'+str(pid)).exists(),'Serialize model requests'
assert (old/'summary.json').exists()and (negative/'summary.json').exists()
assert json.loads((negative/'summary.json').read_text())['passed']
for n in ['defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','native-vwa-request.json','plan80.json']:
 assert(release/n).read_bytes()==(prior/n).read_bytes(),n
assert(release/'run_vwa_pilot.py').read_text().replace(',probe_completion=True','')==(prior/'run_vwa_pilot.py').read_text()
def value(path,name):
 tree=ast.parse(path.read_text());return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in n.targets)))
# VERIFY is a string concatenation with EVIDENCE, so execute only the pure prompt module.
before={};after={};exec((prior/'defense/prompts.py').read_text(),before);exec((release/'defense/prompts.py').read_text(),after)
assert before['VERIFY']==after['VERIFY'],'Main-verifier reuse requires exact unchanged prompt'
source=pathlib.Path(SOURCE);assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCEHASH
out=old.parent/('completion-probe-'+str(time.time_ns()));log=out.with_suffix('.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'completion_probe_replay.py'),'--source',str(source),'--previous',str(old),'--root',str(out),'--token-file',str(old.parent/'transport.token')],cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'time':time.time(),'previous_main_controls':str(old),'negative_control':str(negative),'source_sha256':SOURCEHASH,'scope':'new image-only completion path, unchanged main requests/results reused by exact input equality; development only'}))
'''.replace('OLD',repr(old['root'])).replace('NEGATIVE',repr(negative['root'])).replace('RELEASE',repr(stage['release'])).replace('PRIOR',repr(old['release'])).replace('PIDS',repr(pids)).replace('SOURCEHASH',repr(old['source_sha256'])).replace('SOURCE',repr(json.loads((r/'v3.4.1-sorted-obligation-pause.json').read_text())['attempt']+'/events.jsonl'))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
