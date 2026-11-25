"""Preserve the completed negative-control failure before the next repair."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.5-counterexample-preservation.json'
assert not receipt.exists()
launch=json.loads((r/'v3.5-comparison-launch.json').read_text())
code=r'''
import pathlib,json,hashlib,time
root=pathlib.Path(ROOT);case=root/'withheld_lower_price_frame-result.json'
assert not json.loads(case.read_text())['passed_predeclared_expectation']
dest=root.parent/('v35-counterexample-preservation-'+str(time.time_ns()));dest.mkdir()
paths=[case,root/'actual_sorted_full-result.json',root/'manifest.json',root/'withheld_lower_price_frame/events.jsonl']
hashes={}
for i,p in enumerate(paths):
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(dest/(str(i)+'-'+p.name)).write_bytes(raw)
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps({'time':time.time(),'root':str(dest),'source':str(root),'hashes':hashes,'scope':'failed reference-ablation control retained; no unchanged semantic retry'}))
'''.replace('ROOT',repr(launch['root']))
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
