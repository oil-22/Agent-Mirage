import base64,io,json,time,zipfile
from manage import HERE,REMOTE,remote,save,sha
current=json.loads((HERE/'deployment-current.json').read_bytes());publication=HERE/current['publication'].split('\\')[-1]
files=[HERE/'README.md',HERE/'Flash单图门控框架部署与接线验证-20261113.md',HERE/'deployment-current.json',publication/'deployment.json',publication/'cpu-tests.json',publication/'cpu-tests.stdout.txt',publication/'cpu-tests.stderr.txt',publication/'publication-seal.json']
b=io.BytesIO();manifest={}
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
 for p in files:
  name=p.name;z.writestr(name,p.read_bytes());manifest[name]=sha(p)
payload=base64.b64encode(b.getvalue()).decode()
code=r'''
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
r=Path(ROOT);d=r/DELIVERY;d.mkdir(exist_ok=False)
z=zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)));manifest=MANIFEST
for name in z.namelist():
 p=d/name
 assert p.parent==d
 with p.open('xb')as f:f.write(z.read(name))
 assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest[name]
with(d/'manifest.json').open('x')as f:json.dump(manifest,f,indent=2)
for name in ['README.md','Flash单图门控框架部署与接线验证-20261113.md']:
 with(r/name).open('xb')as f:f.write((d/name).read_bytes())
with(r/'deployment-current.json').open('x')as f:json.dump({'publication':str(d),'deployment':str(d/'deployment.json'),'status':'deployed_ready','old_GUI_goal':'user_paused_not_resumed','mirage_reduction':None},f,indent=2)
print(json.dumps({'delivery':str(d),'files':len(manifest),'time':time.time()}))
'''.replace('ROOT',repr(REMOTE)).replace('DELIVERY',repr('delivery-'+publication.name)).replace('PAYLOAD',repr(payload)).replace('MANIFEST',repr(manifest))
out,d=remote(code,'deliver-report-and-configuration');save(HERE/'remote-delivery-receipt.json',{**json.loads(out),'operation':str(d),'files':manifest});print(out)
