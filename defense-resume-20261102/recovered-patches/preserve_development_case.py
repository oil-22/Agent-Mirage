"""Copy and hash a finished failed development case before changing its algorithm."""
import argparse,json
from pathlib import Path
from remote import remote
p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('case');p.add_argument('output');p.add_argument('--technical',action='store_true');a=p.parse_args()
assert '/'not in a.case and '\\'not in a.case and a.case not in {'.','..'}
r=Path(__file__).resolve().parent;receipt=r/a.output;assert not receipt.exists()
launch=json.loads((r/a.receipt).read_text())
code=r'''
import pathlib,json,hashlib,time
root=pathlib.Path(ROOT);case=CASE;result=root/(case+'-result.json')
if TECHNICAL:
 assert not pathlib.Path('/proc/'+str(PID)).exists()
 assert not result.exists()and 'Traceback'in pathlib.Path(LOG).read_text()
else:assert not json.loads(result.read_text())['passed_predeclared_expectation']
dest=root.parent/('failed-case-preservation-'+str(time.time_ns()));dest.mkdir()
paths=[root/'manifest.json',pathlib.Path(LOG)]+([result]if result.exists()else[])+list((root/case).glob('*'))
hashes={}
for i,p in enumerate(paths):
 if not p.is_file():continue
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(dest/(str(i)+'-'+p.name)).write_bytes(raw)
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps({'root':str(dest),'source':str(root),'case':case,'hashes':hashes,'time':time.time()}))
'''.replace('ROOT',repr(launch['root'])).replace('CASE',repr(a.case)).replace('TECHNICAL',repr(a.technical)).replace('PID',repr(launch['pid'])).replace('LOG',repr(launch['log']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='hashes'}))
