"""Preserve exited pre-inference startup failure before a linked technical repair."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent
launch=json.loads((BASE/'native-direction-development/launch-current.json').read_bytes())
health=json.loads((BASE/'defense-service-resumed-health-current.json').read_bytes())
assert health['requests']==0
code=r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
r=Path(LAUNCH['root']);assert not(Path('/proc')/str(LAUNCH['pid'])).exists()
assert not(r/'status.json').exists() and not(r/'journal').exists()
assert "KeyError: 'DATASET'" in (r/'worker.log').read_text()
files={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file()}
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
 for n in files:z.writestr(n,(r/n).read_bytes())
print(json.dumps({'sha256':files,'zip':base64.b64encode(b.getvalue()).decode(),'new_model_calls':0,'process_exited':True,'root':str(r),'failure':'Missing native browser import DATASET environment before inference'}))
'''
row=json.loads(remote('LAUNCH='+repr(launch)+'\n'+code,host='4090'))
out=BASE/('native-direction-worker-startup-failure-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
    for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
    z.extractall(out)
for n,h in row['sha256'].items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h
(out/'postexit-seal.json').write_text(json.dumps(row,indent=2))
(out/'launcher.py').write_bytes((BASE/'launch_native_direction_development.py').read_bytes())
pointer={'directory':str(out),'seal_sha256':hashlib.sha256((out/'postexit-seal.json').read_bytes()).hexdigest(),'failed_launch':launch,'new_model_calls':0,'service_health':health}
(BASE/'native-direction-development/worker-startup-failure-current.json').write_text(json.dumps(pointer,indent=2))
print(json.dumps({'preserved':str(out),'files':len(row['sha256']),'calls':0}))
