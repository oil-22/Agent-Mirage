"""Download selected public evidence for independent review. No private ledger/config."""
from pathlib import Path
import base64,json
from remote import remote
r=Path(__file__).resolve().parent;launch=json.loads((r/'v2-replay-launch.json').read_text())
manifest=json.loads(remote('import pathlib\nprint((pathlib.Path('+repr(launch['root'])+')/"manifest.json").read_text())',host='4090'))
root=r/('public-review-'+Path(launch['root']).name);root.mkdir(exist_ok=True)
for row in manifest:
    code='''import pathlib,json,base64
p=pathlib.Path(SOURCE);es=[json.loads(x)for x in p.read_text().splitlines()]
pub=next(e['data']['public']for e in es if e['kind']=='observation'and e['data']['public']['observation_id']==OBS)
candidates=[e['data']for e in es if e['kind']=='candidate'and e['data']['observation_id']==OBS]
print(json.dumps({'public':pub,'candidates':candidates,'images':[base64.b64encode((p.parent/(im['sha256']+'.image')).read_bytes()).decode()for im in pub['images']]}))
'''.replace('SOURCE',repr(row['source'])).replace('OBS',repr(row['observation_id']))
    data=json.loads(remote(code,host='4090'));d=root/row['category'];d.mkdir(exist_ok=True)
    for i,raw in enumerate(data.pop('images')):(d/f'image-{i}.png').write_bytes(base64.b64decode(raw))
    (d/'public.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    texts=[]
    for i,m in enumerate(data['public']['messages']):
        content=m['content'];parts=[content]if isinstance(content,str)else [b.get('text','[delivered image]')for b in content]
        texts.append(f'{i} {m["role"]}: '+ '\n'.join(parts))
    texts.extend('CANDIDATE: '+x['text']for x in data['candidates'])
    (d/'review.txt').write_text('\n\n'.join(texts),encoding='utf-8')
(root/'manifest.json').write_text(json.dumps(manifest,indent=2));print(root)
