import hashlib,json
from pathlib import Path
b=Path.cwd();s=Path(json.loads((b/'source14-completion-0090-source-created.json').read_text(encoding='utf8'))['root']);x=json.loads((s/'payload.json').read_text(encoding='utf8'))
p=Path(json.loads((b/'source14-postcheck-0079-source-created.json').read_text(encoding='utf8'))['root']);ref=json.loads((p/'payload.json').read_text(encoding='utf8'))
print('SYSTEM',x['system'])
print('CANDIDATE',x['candidate'])
print('MESSAGES_COUNT',len(x['view']['messages']),'MATCHES_REVIEWED_0079',x['view']['messages']==ref['view']['messages'])
print('IMAGE_INVENTORY_EQUAL',[(v['role'],v['sha256']) for v in x['view']['images']]==[(v['role'],v['sha256']) for v in ref['view']['images']])
print('OTHER_VIEW',json.dumps({k:v for k,v in x['view'].items() if k not in ['images','messages']},ensure_ascii=False))
for i,(a,c) in enumerate(zip(x['view']['messages'],ref['view']['messages'])):
    if a==c:continue
    print('CHANGED_MESSAGE',i,'ROLE',a['role'])
    content=a['content']
    if isinstance(content,str):print(content)
    else:
        for j,block in enumerate(content):
            if block.get('type')=='text':print('TEXTBLOCK',j,block['text'])
            else:print('NONTEXTBLOCK',j,block.get('type'),hashlib.sha256(json.dumps(block,sort_keys=True).encode()).hexdigest())
