import json,pathlib,collections
r=pathlib.Path('/data/researcher/attention-audit-20261102/native-button-metadata/mirage-trace/Qwen3.5-9B/VisualWebArena__buttons_only')
counts=collections.Counter();examples=[]
for p in r.glob('**/model_delivery.jsonl'):
 d=[json.loads(x) for x in p.read_text().splitlines() if x.strip()];fire=[x for x in d if x.get('injection_fired')]
 counts[str(p.relative_to(r)).split('/')[1]]+=len(fire)
 if fire:examples.append((str(p),fire[0]))
print(counts);print(json.dumps(examples[:4],ensure_ascii=False,indent=2));print('files',len(list(r.glob('**/model_delivery.jsonl'))))
