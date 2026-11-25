"""Export sealed, lawful source packets from one already terminal GUI run.

Read-only on both servers. No model, browser, scorer or GPU operation.
"""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


def main():
    run = sys.argv[1]
    assert run in {q['run_id'] for q in json.loads((HERE/'package/plan.json').read_bytes())['queue']}
    pointer = HERE/('source-packets-'+run+'-current.json')
    assert not pointer.exists(), 'Use the existing sealed source packets'
    m = manifest()
    root = HERE/('source-packets-'+run+'-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    prefix = 'RUN='+repr(run)+'\n'
    code = prefix+'P='+repr(m['package4090'])+'\n'+r'''
import hashlib,json,os
from pathlib import Path
p=Path(P)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert os.getuid()==1015
attempts=list((p/'batch/runs'/RUN).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];seal=json.loads((a/'seal.json').read_bytes())
assert {str(q.relative_to(a))for q in a.rglob('*')if q.is_file()and q!=a/'seal.json'}==set(seal)
for n,h in seal.items():assert sha(a/n)==h,n
head='0'*64;events=[]
for n,line in enumerate((a/'controller/events.jsonl').read_bytes().splitlines()):
 row=json.loads(line);value={k:v for k,v in row.items()if k!='sha256'}
 assert row['seq']==n and row['previous']==head and row['sha256']==hashlib.sha256(canon(value)).hexdigest()
 head=row['sha256'];events.append(row)
terminal=json.loads((a/'terminal.json').read_bytes())
safe={k:v for k,v in terminal.items()if k not in ['official_reward','scoring_status','scoring_error','actor_receipts','Flash_replies']}
print(json.dumps({'attempt':str(a),'attempt_seal_sha256':sha(a/'seal.json'),'attempt_members':len(seal),'terminal':safe,'terminal_sha256':sha(a/'terminal.json'),'events':events,'chain_head':head,'new_model_GUI_calls':0}))
'''
    raw, op = remote('4090',code,'late-corruption-source-packets-sealed-GUI',timeout=50)
    gui = json.loads(raw)
    save(root/'GUI.json', {'operation':str(op),'result':gui})
    replies = [r for r in gui['events'] if r['kind']=='actual_actor_reply']
    names = [Path(r['data']['receipt']).name for r in replies]
    code = prefix+'P='+repr(m['package3090'])+'\nO='+repr(m['output3090'])+'\nNAMES='+repr(names)+'\n'+r'''
import base64,hashlib,json,os
from pathlib import Path
p=Path(P);o=Path(O)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert os.getuid()==1033
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
   raw=base64.b64decode(part['image_url']['url'].split(',',1)[1],validate=True);h=hashlib.sha256(raw).hexdigest();assert raw.startswith(b'\x89PNG\r\n\x1a\n')
   images.setdefault(h,base64.b64encode(raw).decode());all_images.append(h);part['image_url']={'source_png_sha256':h,'file':'images/'+h+'.png'}
 rows.append({'folder':str(d),'receipt_seal_sha256':sha(d/'seal.json'),'wire_sha256':sha(d/'wire-request.bin'),'body_sha256':hashlib.sha256(canon(b)).hexdigest(),'request_id':r['request_id'],'decision':index,'native_text':r['text'],'body_with_exact_PNG_references':copy,'all_image_sha256s':all_images,'current_image_sha256':all_images[-1]})
print(json.dumps({'run':item,'public_task':task,'requests':rows,'images':images,'new_model_GUI_calls':0}))
'''
    # Long original histories contain large sealed forward tensors. Keep every
    # original byte check and allow the read-only SSH reader enough I/O time.
    raw, op = remote('3090',code,'late-corruption-lawful-full-history-PNG-export',timeout=240)
    actor = json.loads(raw)
    images = actor.pop('images')
    (root/'images').mkdir()
    for h, encoded in images.items():
        data = base64.b64decode(encoded,validate=True)
        assert hashlib.sha256(data).hexdigest()==h
        (root/'images'/(h+'.png')).write_bytes(data)
    request_events = [r for r in gui['events']if r['kind']=='actual_actor_request']
    for row, reply, request in zip(actor['requests'],replies,request_events):
        assert row['request_id']==reply['data']['request_id']==request['data']['request_id']
        assert row['body_sha256']==request['data']['body_sha256']
        assert hashlib.sha256(row['native_text'].encode()).hexdigest()==reply['data']['text_sha256']
    assert len(actor['requests'])==len(replies)==len(request_events)
    save(root/'actor.json',{'operation':str(op),'result':actor})
    save(root/'summary.json',{'run_id':run,'complete_replies':len(replies),'unique_original_delivered_PNGs':len(images),'full_lawful_histories_exported':True,'semantic_labels_not_provided':True,'official_score_not_in_reviewer_packet':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{str(q.relative_to(root)).replace('\\','/'):sha(q)for q in root.rglob('*')if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'root':str(root),'replies':len(replies),'unique_PNGs':len(images),'semantic_review_pending':True,'new_model_GUI_calls':0}))


if __name__=='__main__':main()
