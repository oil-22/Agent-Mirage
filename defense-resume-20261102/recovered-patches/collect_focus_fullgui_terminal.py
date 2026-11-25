"""Seal the completed fullGUI attempt once; preserve all remote files, collect public artifacts."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
assert not(PREP/'terminal-current.json').exists()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
code=r'''
import base64,hashlib,io,json,os,zipfile,time
from pathlib import Path
r=Path(LAUNCH['root']);p=Path('/proc')/str(LAUNCH['pid']);assert not p.exists(),'Worker must exit before seal'
state=json.loads((r/'status.json').read_bytes());assert state['phase']=='completed'
files={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in r.rglob('*')if f.is_file()}
seal=r/'postexit-terminal-sha256.json';assert not seal.exists();seal.write_text(json.dumps(files,indent=2))
collected=[n for n in files if not n.endswith(('.pkl','.zip'))]+['postexit-terminal-sha256.json']
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in collected:z.writestr(n,(r/n).read_bytes())
print(json.dumps({'root':str(r),'sealed_files':len(files),'collected_files':len(collected),'terminal_sha256':hashlib.sha256(seal.read_bytes()).hexdigest(),'zip':base64.b64encode(buf.getvalue()).decode()}))
'''
row=json.loads(remote('LAUNCH='+repr(launch)+'\n'+code,host='4090',timeout=60))
out=PREP/('terminal-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
 for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
 z.extractall(out)
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((out/'postexit-terminal-sha256.json').read_bytes())==row['terminal_sha256']
for n,h in json.loads((out/'postexit-terminal-sha256.json').read_bytes()).items():
 if(out/n).exists():assert sha((out/n).read_bytes())==h,n
row['directory']=str(out);(PREP/'terminal-current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
