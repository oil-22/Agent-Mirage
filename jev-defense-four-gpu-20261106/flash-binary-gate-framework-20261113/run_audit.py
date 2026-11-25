import base64,json
from manage import HERE,REMOTE,remote,save
payload=base64.b64encode((HERE/'audit_runtime.py').read_bytes()).decode()
code=r'''
import base64,json,os,subprocess
from pathlib import Path
r=Path(ROOT);script=r/'audit_runtime.py'
with script.open('xb')as f:f.write(base64.b64decode(PAYLOAD))
env=dict(os.environ);env['CUDA_VISIBLE_DEVICES']='';env['PYTHONDONTWRITEBYTECODE']='1'
with(r/'audit-runtime.log').open('xb')as log:
 p=subprocess.Popen(['/home/researcher/jev-defense-four-gpu-20261106/flash-preparation/env-flash-01/bin/python','-B','-u',str(script),str(r)],env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
with(r/'audit-launch.json').open('x')as f:json.dump({'pid':p.pid},f)
print(json.dumps({'pid':p.pid}))
'''.replace('ROOT',repr(REMOTE)).replace('PAYLOAD',repr(payload))
out,d=remote(code,'launch-cpu-audit');save(HERE/'audit-launch-receipt.json',{**json.loads(out),'evidence':str(d)});print(out)
