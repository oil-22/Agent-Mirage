import json,hashlib
from pathlib import Path
root=Path(__file__).parent;src=root/'judge-legal-projection-linked03/review/judges'
out=[]
for index in (39,45,55,69,70,72,73):
 p=src/f'{index:03}.json';d=json.loads(p.read_bytes());v=d['actual_native_payload']['view']
 messages=[]
 for i,m in enumerate(v['messages']):
  c=m['content']
  if m['role']=='assistant':messages.append({'message_index':i,'role':m['role'],'content':c})
 out.append({'judge_index':index,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'phase':d['phase'],'assistant_reports_with_actual_indices':messages})
dest=root/'history-source-review.json';assert not dest.exists();dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out[-1],ensure_ascii=False,indent=2))
