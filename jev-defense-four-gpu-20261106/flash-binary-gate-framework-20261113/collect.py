"""Copy a point-in-time snapshot including new full wire/tensor evidence."""
import base64,io,json,time,zipfile
from pathlib import Path
from manage import HERE,REMOTE,remote,save,sha
code=r'''
import base64,hashlib,io,json,zipfile,time
from pathlib import Path
r=Path(ROOT);files={};b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
 for p in r.rglob('*'):
  if not p.is_file()or p.name=='token'or '__pycache__'in p.parts:continue
  name=str(p.relative_to(r));raw=p.read_bytes();files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};z.writestr(name,raw)
print(json.dumps({'time':time.time(),'files':files,'zip':base64.b64encode(b.getvalue()).decode()}))
'''.replace('ROOT',repr(REMOTE))
out,op=remote(code,'collect-point-in-time-evidence',timeout=55);v=json.loads(out);destination=HERE/('evidence-'+str(time.time_ns()));destination.mkdir()
z=zipfile.ZipFile(io.BytesIO(base64.b64decode(v.pop('zip'))))
for n in z.namelist():
 p=destination/n
 if not p.resolve().is_relative_to(destination.resolve()):raise ValueError('Invalid evidence path')
 p.parent.mkdir(exist_ok=True,parents=True)
 with p.open('xb')as f:f.write(z.read(n))
 assert sha(p)==v['files'][n]['sha256']
save(destination/'snapshot-manifest.json',v)
save(HERE/('collection-'+str(time.time_ns())+'.json'),{'evidence':str(destination),'files':len(v['files']),'operation':str(op),'manifest_sha256':sha(destination/'snapshot-manifest.json')})
print(json.dumps({'evidence':str(destination),'files':len(v['files'])}))
