"""Export only sealed completed requests from a live GUI prefix, read-only.

The terminal exporter remains unchanged. A prefix review is not a trajectory
verdict, and never sends labels or evidence back to either model.
"""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


def main():
    run, count = sys.argv[1], int(sys.argv[2])
    m = manifest()
    plan = json.loads((HERE/'package/plan.json').read_bytes())
    assert run in {v['run_id'] for v in plan['queue']} and 0 < count <= 50
    pointer = HERE/('source-prefix-'+run+'-'+str(count)+'-current.json')
    assert not pointer.exists(), 'Use the existing immutable prefix'
    root = HERE/('source-prefix-'+run+'-'+str(count)+'-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    prefix = 'RUN='+repr(run)+'\nCOUNT='+repr(count)+'\n'
    code = prefix+'P='+repr(m['package4090'])+'\n'+r'''
import hashlib,json,os
from pathlib import Path
assert os.getuid()==1015
p=Path(P);attempts=list((p/'batch/runs'/RUN).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];q=a/'controller/events.jsonl';raw=q.read_bytes();raw=raw[:raw.rfind(b'\n')+1]
events=[];head='0'*64
for n,line in enumerate(raw.splitlines()):
 row=json.loads(line);value={k:v for k,v in row.items()if k!='sha256'}
 assert row['seq']==n and row['previous']==head and row['sha256']==hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 head=row['sha256'];events.append(row)
replies=[r for r in events if r['kind']=='actual_actor_reply'];assert len(replies)>=COUNT
end=replies[COUNT-1]['seq'];events=events[:end+1]
requests=[r for r in events if r['kind']=='actual_actor_request'];assert len(requests)==COUNT
print(json.dumps({'attempt':str(a),'verified_log_prefix_bytes':len(raw),'verified_log_prefix_sha256':hashlib.sha256(raw).hexdigest(),'prefix_events':events,'selected_chain_head':events[-1]['sha256'],'selected_completed_replies':COUNT,'whole_trajectory_status_not_inferred':True,'new_model_GUI_calls':0}))
'''
    raw, op = remote('4090',code,'live-prefix-lawful-source-export-GUI',timeout=40)
    gui = json.loads(raw)
    save(root/'GUI.json',{'operation':str(op),'result':gui})
    replies = [r for r in gui['prefix_events'] if r['kind']=='actual_actor_reply']
    requests = [r for r in gui['prefix_events'] if r['kind']=='actual_actor_request']
    names = [Path(r['data']['receipt']).name for r in replies]
    code = prefix+'P='+repr(m['package3090'])+'\nO='+repr(m['output3090'])+'\nNAMES='+repr(names)+'\n'+r'''
import base64,hashlib,json,os
from pathlib import Path
assert os.getuid()==1033
p=Path(P);o=Path(O)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
plan=json.loads((p/'plan.json').read_bytes());item=next(v for v in plan['queue']if v['run_id']==RUN);task=next(v for v in plan['tasks']if v['task_id']==item['task_id'])
rows=[];images={};previous=None;previous_reply=None
for index,name in enumerate(NAMES,1):
 d=o/'primary/requests'/name;seal=json.loads((d/'seal.json').read_bytes())
 assert {str(q.relative_to(d))for q in d.rglob('*')if q.is_file()and q!=d/'seal.json'}==set(seal)
 for n,h in seal.items():assert sha(d/n)==h,n
 w=json.loads((d/'wire-request.bin').read_bytes());b=json.loads((d/'body.json').read_bytes());r=json.loads((d/'response.json').read_bytes())
 assert w['body']==b and w['run_id']==RUN and w['decision_index']==index and r['request_id']==w['request_id'] and r['request_sha256']==sha(d/'wire-request.bin')
 if previous is not None:assert b['messages'][:len(previous['messages'])]==previous['messages']and b['messages'][len(previous['messages'])]=={'role':'assistant','content':previous_reply}
 previous=b;previous_reply=r['text'];copy=json.loads(json.dumps(b));all_images=[]
 for msg in copy['messages']:
  if not isinstance(msg.get('content'),list):continue
  for part in msg['content']:
   if part['type']!='image_url':continue
   data=base64.b64decode(part['image_url']['url'].split(',',1)[1],validate=True);h=hashlib.sha256(data).hexdigest();assert data.startswith(b'\x89PNG\r\n\x1a\n')
   images.setdefault(h,base64.b64encode(data).decode());all_images.append(h);part['image_url']={'source_png_sha256':h,'file':'images/'+h+'.png'}
 rows.append({'folder':str(d),'receipt_seal_sha256':sha(d/'seal.json'),'wire_sha256':sha(d/'wire-request.bin'),'body_sha256':hashlib.sha256(canon(b)).hexdigest(),'request_id':r['request_id'],'decision':index,'native_text':r['text'],'body_with_exact_PNG_references':copy,'all_image_sha256s':all_images,'current_image_sha256':all_images[-1]})
assert len(rows)==COUNT
print(json.dumps({'run':item,'public_task':task,'requests':rows,'images':images,'new_model_GUI_calls':0}))
'''
    raw, op = remote('3090',code,'live-prefix-lawful-full-history-PNG-export',timeout=240)
    actor = json.loads(raw)
    images = actor.pop('images')
    (root/'images').mkdir()
    for h, encoded in images.items():
        data=base64.b64decode(encoded,validate=True)
        assert hashlib.sha256(data).hexdigest()==h
        (root/'images'/(h+'.png')).write_bytes(data)
    for row, reply, request in zip(actor['requests'],replies,requests):
        assert row['request_id']==reply['data']['request_id']==request['data']['request_id']
        assert row['body_sha256']==request['data']['body_sha256']
        assert hashlib.sha256(row['native_text'].encode()).hexdigest()==reply['data']['text_sha256']
    save(root/'actor.json',{'operation':str(op),'result':actor})
    save(root/'summary.json',{'run_id':run,'complete_replies_in_prefix':count,'unique_original_delivered_PNGs':len(images),'full_lawful_histories_exported':True,'semantic_labels_not_provided':True,'official_score_not_in_reviewer_packet':True,'trajectory_semantics_unknown':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{str(q.relative_to(root)).replace('\\','/'):sha(q)for q in root.rglob('*')if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'root':str(root),'replies':count,'unique_PNGs':len(images),'whole_trajectory_unknown':True,'new_model_GUI_calls':0}))


if __name__=='__main__':main()
