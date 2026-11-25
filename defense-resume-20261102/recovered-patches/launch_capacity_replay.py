"""Launch once after validating eight-card runtime metadata and service health."""
import base64
import hashlib
import json
from pathlib import Path
from remote import remote

here=Path(__file__).resolve().parent
receipt=here/'v8-capacity-replay-launch.json'
assert not receipt.exists()
service=json.loads((here/'v8-service-launch.json').read_text())
old=json.loads((here/'v7-service-launch.json').read_text())
raw=(here/'capacity_replay.py').read_bytes()
code='''import pathlib,json,time,hashlib,subprocess,base64,urllib.request
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');service=pathlib.Path(SERVICE);old=pathlib.Path(OLD)
assert json.loads((service/'status.json').read_text())['phase']=='ready'
new=json.loads((service/'runtime.json').read_text());prior=json.loads((old/'runtime.json').read_text())
for key,value in prior.items():
 if key!='device_map':assert new[key]==value,key
assert set(new['device_map'].values())==set(str(i)for i in range(8))
assert new['placement']=='balanced'and new['dtype']=='torch.bfloat16'and new['backend']=='sdpa'
runtime={'time':time.time(),'old_runtime_sha256':hashlib.sha256((old/'runtime.json').read_bytes()).hexdigest(),'new_runtime_sha256':hashlib.sha256((service/'runtime.json').read_bytes()).hexdigest(),'metadata_except_device_map_identical':True,'device_map':new['device_map'],'physical_gpus':list(range(8)),'scope':'Only parameter placement expanded; native generate/judge/handler AST and schema bound at launch. Actual token equivalence still pending.'}
(base/'v8-runtime-equivalence.json').write_text(json.dumps(runtime,indent=2))
token=(base/'transport.token').read_text().strip();health=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18127',headers={'Authorization':'Bearer '+token}),timeout=10))
assert health['phase']=='ready'
out=base/('capacity-replay-v8-'+str(time.time_ns()));script=out.with_suffix('.py');script.write_bytes(base64.b64decode(SCRIPT))
log=out.with_suffix('.log')
env=__import__('os').environ.copy();env['PYTHONPATH']=RELEASE
with log.open('xb')as stream:
 p=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(script),'--old-service',str(old),'--root',str(out),'--token-file',str(base/'transport.token')],cwd=RELEASE,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'log':str(log),'script':str(script),'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'service':str(service),'runtime':runtime,'scope':'One native placement control plus same-byte technical OOM retry, no GUI or whole-task result'}))
'''.replace('SERVICE',repr(service['root'])).replace('OLD',repr(old['root'])).replace('SCRIPT',repr(base64.b64encode(raw).decode())).replace('RELEASE',repr(service['release']))
data=json.loads(remote(code,host='3090'))
receipt.write_text(json.dumps(data,indent=2),encoding='utf-8')
(here/'v8-runtime-equivalence.json').write_text(json.dumps(data['runtime'],indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in data.items()if k!='runtime'}))
