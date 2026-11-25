"""Snapshot terminated development failures before any further repair."""
import argparse,json
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('receipt');ap.add_argument('output');a=ap.parse_args()
here=Path(__file__).resolve().parent;out=here/a.output;assert not out.exists()
r=json.loads((here/a.receipt).read_text())
code=r'''import pathlib,json,hashlib,time
root=pathlib.Path(ROOT);proc=pathlib.Path('/proc')/str(PID)
assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
out=root.parent/('preserved-development-'+root.name+'-'+str(time.time_ns()));out.mkdir();hashes={}
for p in [pathlib.Path(LOG),*root.rglob('*')]:
 if p.is_file():
  raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();q=out/('log.txt'if str(p)==LOG else str(p.relative_to(root)));q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(out/'hashes.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps({'preservation':str(out),'hashes':hashes,'source':str(root)}))
'''.replace('ROOT',repr(r['root'])).replace('LOG',repr(r['log'])).replace('PID',str(r['pid']))
data=json.loads(remote(code,host='4090'));out.write_text(json.dumps(data,indent=2));print(json.dumps({'preservation':data['preservation'],'files':len(data['hashes'])}))
