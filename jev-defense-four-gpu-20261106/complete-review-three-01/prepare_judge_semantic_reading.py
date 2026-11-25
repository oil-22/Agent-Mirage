import json,hashlib
from pathlib import Path
from collections import Counter
root=Path(__file__).parent;src=root/'judge-legal-projection-linked03';dest=root/'judge-semantic-reading-01';assert not dest.exists();dest.mkdir()
seal=json.loads((src/'seal.json').read_bytes());h=lambda b:hashlib.sha256(b).hexdigest()
for n,sha in seal.items():assert h((src/n).read_bytes())==sha
rows=[];systems={};views={};candidates={}
for path in sorted((src/'review/judges').glob('*.json')):
 d=json.loads(path.read_bytes());p=d['actual_native_payload'];v=p['view'];sy=h(p['system'].encode());systems.setdefault(sy,p['system'])
 cand=p['candidate'];ch=h(cand.encode()) if cand is not None else None
 if ch:candidates.setdefault(ch,cand)
 vh=h(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode());views.setdefault(vh,v)
 duplicates=[]
 def hook(pairs):
  seen=set();out={}
  for k,val in pairs:
   if k in seen:duplicates.append(k)
   seen.add(k);out[k]=val
  return out
 parsed=json.loads(d['raw_response'],object_pairs_hook=hook)
 rows.append({'index':int(path.stem),'phase':d['phase'],'decision':d['actual_envelope_without_payload']['decision_index'],
  'observation_id':v['observation_id'],'format_retry':d['format_retry'],'system_sha256':sy,'view_sha256':vh,'candidate_sha256':ch,
  'images':[{'sha256':im['original_raw_image_binding']['original_image_sha256'],'role':im['role']} for im in v['images']],
  'recent_action':v['recent_action'],'execution_feedback':v['execution_feedback'],'parsed_response':parsed,'duplicate_JSON_keys':duplicates,
  'original_source_file':str(path.relative_to(src)),'source_sha256':h(path.read_bytes()),'wire_sha256':d['actual_wire_sha256']})
def save(n,obj):
 (dest/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('index.json',{'count':len(rows),'phase_counts':dict(Counter(r['phase'] for r in rows)),'unique_systems':len(systems),'unique_views':len(views),'unique_candidates':len(candidates),'rows':rows})
save('systems.json',systems);save('views.json',views);save('candidates.json',candidates)
for start in range(0,73,15):
 text=[]
 for r in rows[start:start+15]:
  text.append(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','wire_sha256','original_source_file','system_sha256','view_sha256')},ensure_ascii=False,separators=(',',':')))
 (dest/f'batch-{start+1:03}-{min(start+15,73):03}.jsonl').write_text('\n'.join(text)+'\n',encoding='utf-8')
save('seal.json',{str(p.relative_to(dest)):h(p.read_bytes()) for p in dest.rglob('*') if p.is_file()})
print(json.dumps({'path':str(dest),'count':len(rows),'phase_counts':dict(Counter(r['phase'] for r in rows)),'unique_systems':len(systems),'unique_views':len(views),'unique_candidates':len(candidates),'duplicate_keys_replies':sum(bool(r['duplicate_JSON_keys'])for r in rows)},ensure_ascii=False))
