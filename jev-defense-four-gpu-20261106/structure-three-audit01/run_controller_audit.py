import base64,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
H=Path(__file__).resolve().parent;B=H.parent
R=H/'service-audit-public-1794040226300580000'
POST=B/'three-terminal-postexit-public/1794040388947724400'
S=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
code='''import base64,json
from pathlib import Path
g=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799')
names=['online-admission.json','process.json','primary-launch.json','pplx_flash-launch.json','primary/loaded.json','pplx_flash/loaded.json','primary/stopped.json','pplx_flash/stopped.json','exit.json','launch-specification.json']
files={n:base64.b64encode((g/n).read_bytes()).decode()for n in names}
lease=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
files['resource-lease.json']=base64.b64encode(lease.read_bytes()).decode()
print(json.dumps(files))
'''
extra=json.loads(remote(code,host='3090',timeout=45))
X=H/('service-postexit-meta-'+str(time.time_ns()));X.mkdir(exist_ok=False)
for name,raw in extra.items():
    p=X/name;p.parent.mkdir(exist_ok=True);p.write_bytes(base64.b64decode(raw))
(X/'seal.json').write_text(json.dumps({p.relative_to(X).as_posix():S(p)for p in X.rglob('*')if p.is_file()},indent=2),encoding='utf8')
inputs={
 'service-receipt':R/'receipt.json','request-certificates':R/'request-certificates.json','request-audits':R/'request-audits.json',
 'service-public-seal':R/'seal.json','service-journal':R/'service-journal.jsonl','online-state':R/'online-state.json','loaded':R/'loaded.json',
 'postexit-report':POST/'report.json','service-terminal-manifest':POST/'public/terminal-sha256.json','online-admission':X/'online-admission.json',
}
payload=json.dumps({name:base64.b64encode(p.read_bytes()).decode()for name,p in inputs.items()})
source='INPUTS_BASE64='+repr(base64.b64encode(payload.encode()).decode())+'\n'+(H/'controller_audit_remote.py').read_text(encoding='utf8')
compile(source,'controller_audit_remote.py','exec')
code='''import base64,json,pathlib,subprocess,sys,time
root=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/three-controller-audit-source-'+str(time.time_ns()));root.mkdir(mode=0o700)
p=root/'controller_audit_remote.py';p.write_bytes(base64.b64decode(SOURCE))
r=subprocess.run(['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-B',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(root/'stdout.txt').write_bytes(r.stdout);(root/'stderr.txt').write_bytes(r.stderr)
if r.returncode:
 sys.stdout.buffer.write(r.stdout);sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)
sys.stdout.buffer.write(r.stdout)
'''
result=json.loads(remote('SOURCE='+repr(base64.b64encode(source.encode()).decode())+'\n'+code,timeout=240,host='4090'))
out=H/('controller-audit-public-'+str(time.time_ns()));out.mkdir(exist_ok=False)
for name,b64 in result.pop('files').items():
    assert Path(name).name==name
    (out/name).write_bytes(base64.b64decode(b64))
assert S(out/'audit.json')==result['audit_sha256']and S(out/'seal.json')==result['seal_sha256']
(out.parent/(out.name+'-transfer.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({**result,'local':str(out),'postexit_meta':str(X)}))
