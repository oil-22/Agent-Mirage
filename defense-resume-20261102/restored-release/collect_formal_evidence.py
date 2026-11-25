"""Copy selected formal-run evidence for human review, with source hashes.

Read-only on the server. This exporter never calls the model or changes a run.
"""
import argparse
import base64
import json
from pathlib import Path
from remote import remote

ap = argparse.ArgumentParser()
ap.add_argument('--run-id', required=True)
ap.add_argument('--steps', type=int, nargs='*', default=[])
ap.add_argument('--receipt', default='v2-vwa-launch.json')
ap.add_argument('--output', default='formal-repair-evidence')
args = ap.parse_args()
if '/' in args.run_id or '\\' in args.run_id or args.run_id in {'.', '..'}:
    raise ValueError('A run basename is required')
here = Path(__file__).resolve().parent
launch = json.loads((here / args.receipt).read_text())
code = r'''
import base64,copy,hashlib,json,pathlib
r=pathlib.Path(ROOT)/'runs'/RUN
marker=r/'complete.json'
attempt=pathlib.Path(json.loads(marker.read_text())['attempt']) if marker.exists() else sorted(r.glob('attempt-*'))[-1]
raw=(attempt/'events.jsonl').read_bytes()
events=[json.loads(line)for line in raw.splitlines()]
selected=set(STEPS)
files={}
for p in (attempt/'screenshots').glob('*.png'):
    if not selected or int(p.name[:3])in selected:files[p.name]=p.read_bytes()
final=attempt/'final-actually-captured.png'
if final.exists():files[final.name]=final.read_bytes()
keep={'candidate','decision_accepted','action_executed','decision_blocked','state_invalidated','private_delivery_ledger','protocol','implementation'}
kept=[e for e in events if e['kind']in keep]
observations=[]
for e in events:
    if e['kind']!='observation' or e['data'].get('audience','actor')!='actor':continue
    public=copy.deepcopy(e['data']['public'])
    for message in public['messages']:
        if isinstance(message['content'],list):
            for block in message['content']:
                if block.get('type')=='image_url':
                    url=block['image_url']['url'];block['image_url']['url']='exported-separately; sha256='+hashlib.sha256(base64.b64decode(url.split(',',1)[1])).hexdigest()
    observations.append({'event_seq':e['seq'],'public':public,'artifacts':e['data']['artifacts']})
source_hashes={'events.jsonl':hashlib.sha256(raw).hexdigest()}
for p in [attempt/'complete.json',attempt/'failure.json',attempt/'technical-failure.json',attempt/'paused.json']:
    if p.exists():source_hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({'attempt':str(attempt),'events':kept,'observations':observations,
 'source_sha256':source_hashes,'images':{n:base64.b64encode(v).decode()for n,v in files.items()},
 'image_sha256':{n:hashlib.sha256(v).hexdigest()for n,v in files.items()},
 'complete':json.loads((attempt/'complete.json').read_text())if(attempt/'complete.json').exists()else None},ensure_ascii=False))
'''.replace('ROOT', repr(launch['root'])).replace('RUN', repr(args.run_id)).replace('STEPS', repr(args.steps))
data = json.loads(remote(code, host='4090'))
data['source_batch']=launch['root']
data['launch_receipt']=args.receipt
out = here / args.output / args.run_id
out.mkdir(parents=True, exist_ok=True)
for name, encoded in data.pop('images').items():
    (out / name).write_bytes(base64.b64decode(encoded))
(out / 'evidence.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'output':str(out),'attempt':data['attempt'],
 'images':len(data['image_sha256']),'completed':data['complete'] is not None},ensure_ascii=False))
