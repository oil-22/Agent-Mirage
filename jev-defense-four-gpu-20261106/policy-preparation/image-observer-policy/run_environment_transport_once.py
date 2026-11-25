"""Stage an exclusive new source file and execute one authorized native transport check."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'environment_transport_preflight.py';raw=source.read_bytes()
remote='/data/researcher/jev-defense-four-gpu-20261106/environment-transport-source-'+str(time.time_ns())+'.py'
stage='''import base64,hashlib,os,sys
from pathlib import Path
raw=base64.b64decode(PAYLOAD)
assert hashlib.sha256(raw).hexdigest()==EXPECTED
path=Path(TARGET)
with path.open('xb')as f:f.write(raw)
os.execv(sys.executable,[sys.executable,str(path)])
'''.replace('PAYLOAD',repr(base64.b64encode(raw).decode())).replace('EXPECTED',repr(hashlib.sha256(raw).hexdigest())).replace('TARGET',repr(remote))
cmd=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
     '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python -']
r=subprocess.run(cmd,input=stage,text=True,capture_output=True,timeout=360)
evidence=ROOT/('environment-transport-launch-'+str(time.time_ns()));evidence.mkdir()
(evidence/'stdout.txt').write_text(r.stdout,encoding='utf8');(evidence/'stderr.txt').write_text(r.stderr,encoding='utf8')
(evidence/'launch.json').write_text(json.dumps({'source_sha256':hashlib.sha256(raw).hexdigest(),
    'remote_source':remote,'returncode':r.returncode,'automatic_retry':False},indent=2),encoding='utf8')
print(r.stdout)
print(json.dumps({'local_launch_evidence':str(evidence),'returncode':r.returncode,'automatic_retry':False}))
if r.returncode:raise SystemExit(r.returncode)
