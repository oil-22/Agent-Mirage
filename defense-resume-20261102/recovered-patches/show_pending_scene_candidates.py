"""Read public-only novel candidate packets, excluding base64 and checker outcomes."""
import hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'scene-only-fullgui-development'
pointer=json.loads((P/'public-candidates-current.json').read_bytes());d=Path(pointer['directory'])
assert hashlib.sha256((d/'sha256.json').read_bytes()).hexdigest()==pointer['manifest_sha256']
reviewed={json.loads(p.read_bytes())['candidate_seq']for p in(P/'semantic-review-batches').glob('*/review.json')}
for x in json.loads((d/'packets.json').read_bytes()):
 if x['candidate_seq']in reviewed:continue
 p=x['public'];messages=[]
 for i,m in enumerate(p['messages']):
  c=m['content'];messages.append({'original_index':i,'role':m['role'],'text':c if isinstance(c,str)else[v.get('text','[original image]')for v in c]})
 print(json.dumps({'candidate_seq':x['candidate_seq'],'candidate':x['candidate'],'source_directory':str(d),'public':{k:v for k,v in p.items()if k!='messages'},'messages':messages},ensure_ascii=True))
