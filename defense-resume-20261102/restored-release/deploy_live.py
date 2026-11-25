"""Stage frozen releases and native environment preflight; no paid APIs."""
import base64,hashlib,json,secrets
from pathlib import Path
from remote import remote
R=Path(__file__).resolve().parent
token=R/'transport.token'
if not token.exists():token.write_text(secrets.token_hex(32))
source=R.parent/'qwen27-attention-pilot-20261020/inputs/cases/classifieds_100/requests/002.json'
body=json.loads(source.read_text());body['messages']=[body['messages'][0]]
(R/'native-vwa-request.json').write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf-8')
names=['defense/__init__.py','defense/core.py','defense/prompts.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py','run_vwa_pilot.py','plan80.json','native-vwa-request.json']
files={n:base64.b64encode((R/n).read_bytes()).decode()for n in names};release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
def stage(host,root):
 code='''import base64,json,pathlib,os,py_compile
r=pathlib.Path(ROOT);p=r/'releases'/RELEASE;p.mkdir(parents=True,exist_ok=True)
for name,data in json.loads(PAYLOAD).items():
 out=p/name;out.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(data)
 if out.exists():assert out.read_bytes()==raw
 else:out.write_bytes(raw)
 if name.endswith('.py'):py_compile.compile(str(out),doraise=True)
t=r/'transport.token'
if t.exists():assert t.read_text()==TOKEN
else:t.write_text(TOKEN);os.chmod(t,0o600)
print(json.dumps({'root':str(r),'release':str(p)}))
'''.replace('ROOT',repr(root)).replace('RELEASE',repr(release)).replace('PAYLOAD',repr(json.dumps(files))).replace('TOKEN',repr(token.read_text()))
 return json.loads(remote(code,host=host))
staged={host:stage(host,root)for host,root in [('3090','/home/researcher/mirage-defense-pilot-20261023'),('4090','/data/researcher/mirage-defense-pilot-20261023')]}
(R/'live-staging.json').write_text(json.dumps(staged,indent=2));print(json.dumps(staged,indent=2))
code='''import pathlib,subprocess,os,json,time
r=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);attempt=r/('environment-preflight-'+str(time.time_ns()));attempt.mkdir()
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
with (attempt/'worker.log').open('xb')as out:
 child=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(attempt),'--plan',str(release/'plan80.json'),'--token-file',str(r/'transport.token'),'--environment-preflight'],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=child.pid,root=str(attempt),release=str(release),phase='environment_preflight_launched',time=time.time());(r/'environment-launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
'''.replace('ROOT',repr(staged['4090']['root'])).replace('RELEASE',repr(staged['4090']['release']))
receipt=json.loads(remote(code,host='4090'));(R/'environment-launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
