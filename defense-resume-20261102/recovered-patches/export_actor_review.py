"""Export actual actor inputs/replies for review, excluding private detector/score data.

Correction text actually supplied to the actor is retained, so blinding is limited.
No labels are inferred; prepared screenshots with no actor request are not exposures.
"""
import argparse,base64,hashlib,json,time
from pathlib import Path
from remote import remote
ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);ap.add_argument('--receipt',default='v3.8.3-vwa-resume.json');a=ap.parse_args()
assert '/'not in a.run_id and '\\'not in a.run_id
here=Path(__file__).resolve().parent;launch=json.loads((here/a.receipt).read_text())
code=r'''import pathlib,copy,json,hashlib,base64
run=pathlib.Path(ROOT)/'runs'/RUN;marker=run/'complete.json'
attempt=pathlib.Path(json.loads(marker.read_text())['attempt'])if marker.exists()else sorted(run.glob('attempt-*'))[-1]
raw=(attempt/'events.jsonl').read_bytes();events=[];partial=False
for line in raw.splitlines():
 try:events.append(json.loads(line))
 except json.JSONDecodeError:partial=True
rows=[];images={}
for i,event in enumerate(events):
 if event['kind']!='actor_request':continue
 public=event['data']['public'];response=next((e for e in events[i+1:]if e['kind']in {'candidate','actor_request'}),None)
 if not response or response['kind']!='candidate':continue
 assert response['data']['observation_id']==public['observation_id']
 messages=copy.deepcopy(public['messages'])
 for message in messages:
  if not isinstance(message['content'],list):continue
  for block in message['content']:
   if block.get('type')!='image_url':continue
   url=block['image_url'];url=url['url']if isinstance(url,dict)else url
   image=base64.b64decode(url.split(',',1)[1]);sha=hashlib.sha256(image).hexdigest()
   assert(attempt/(sha+'.image')).read_bytes()==image
   images[sha]=base64.b64encode(image).decode();block['image_url']={'url':'images/'+sha+'.png'}
 rows.append({'index':len(rows)+1,'messages':messages,'response':response['data']['text'],'review_label':None,'pure_model_wait':None,'review_notes':None})
print(json.dumps({'attempt':str(attempt),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'partial_last_line':partial,'completed_marker':marker.exists(),'rows':rows,'images':images}))
'''.replace('ROOT',repr(launch['root'])).replace('RUN',repr(a.run_id))
data=json.loads(remote(code,host='4090'));identity=hashlib.sha256(data['attempt'].encode()).hexdigest()[:12]
snapshot=here/'actor-review-snapshots'/(identity+'-'+str(time.time_ns()));public=snapshot/'review';(public/'images').mkdir(parents=True)
images=data.pop('images')
for sha,encoded in images.items():
    raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==sha;(public/'images'/(sha+'.png')).write_bytes(raw)
rows=data.pop('rows');(snapshot/'private-provenance.json').write_text(json.dumps({'run_id':a.run_id,'receipt':a.receipt,**data},indent=2),encoding='utf-8')
(public/'actor-inputs-and-replies.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# Actor轨迹审查包', '', '只包含实际提交给actor的完整消息及其原始回复。保留真实交付的纠正文字，因此无法保证完全盲审。未包含检测器结论、注入真值、官方分数或arm标签。所有语义标签待审查；纯模型WAIT排除，后来纠正不抵消首次错误。', '']
for row in rows:
    md += ['## 候选 '+str(row['index']),'']
    for message in row['messages']:
        blocks=message['content']if isinstance(message['content'],list)else[{'type':'text','text':message['content']}]
        for block in blocks:
            if block.get('type')=='image_url':md += ['![实际输入图片]('+str((public/block['image_url']['url']).resolve()).replace('\\','/')+')','']
    md += [row['response'],'','完整历史见同目录JSON；Mirage及WAIT标签均待审查。','']
(public/'轨迹.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'snapshot':str(snapshot),'public_review':str(public),'actual_actor_replies':len(rows),'images':len(images),'completed':data['completed_marker'],'labels':'unreviewed','scope':'Actor input/reply export only; no semantic result or efficacy estimate'}))
