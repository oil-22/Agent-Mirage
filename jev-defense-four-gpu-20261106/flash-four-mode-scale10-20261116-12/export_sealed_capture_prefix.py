"""Read-only review export of sealed individual captures; no terminal claim.

This lets usability review proceed while a long trajectory continues. Every
image must later match the ordinary sealed-terminal/full-request audit.
"""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE,manifest,remote,save,sha

CODE=r'''
import base64,hashlib,json,time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def stable(p):
 before=p.stat();raw=p.read_bytes();after=p.stat()
 keys=['st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns']
 assert all(getattr(before,k)==getattr(after,k)for k in keys),str(p)
 return raw
def sha(p):return hashlib.sha256(stable(p)).hexdigest()
p=Path(P);assert sha(p/'manifest.json')==MANIFEST
m=json.loads((p/'manifest.json').read_bytes())
assert sha(p/'capture_source.py')==m['files']['capture_source.py']
attempts=list((p/'batch/runs'/RUN).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];journal=(a/'controller/events.jsonl').read_bytes();events=[];head='0'*64;sealed_lines=[]
for i,line in enumerate(journal.splitlines(keepends=True)):
 if not line.endswith(b'\n'):break
 event=json.loads(line);h=event.pop('sha256')
 assert event['seq']==i and event['previous']==head and hashlib.sha256(canonical(event)).hexdigest()==h
 head=h;events.append(event);sealed_lines.append(line)
ready=json.loads(stable(a/'trusted-source/ready.json'))
assert ready['fixture']is False and ready['source_code_sha256']==m['files']['capture_source.py']
key=Ed25519PublicKey.from_public_bytes(bytes.fromhex(ready['public_key']))
assert hashlib.sha256(bytes.fromhex(ready['public_key'])).hexdigest()==ready['key_id']
images={};frames=[]
for event in events:
 if event['kind']!='PRIVATE_capture_injection':continue
 d=event['data'];cid=d['capture_id'];folder=a/'trusted-source'/('capture-'+cid)
 # A completed per-capture seal is required even though the episode is live.
 members=json.loads(stable(folder/'seal.json'))
 for n,h in members.items():assert sha(folder/n)==h
 receipt=json.loads(stable(folder/'receipt.json'))
 key.verify(bytes.fromhex(receipt['signature']),canonical({k:v for k,v in receipt.items()if k!='signature'}))
 assert receipt['capture_id']==cid and receipt['source_code_sha256']==ready['source_code_sha256']
 assert receipt['session_id']==ready['session_id']and receipt['environment_id']==ready['environment_id']
 stem='%04d'%d['capture_index']
 assert receipt==json.loads(stable(a/'capture-deliveries'/(stem+'-signed-receipt.json')))
 expected=json.loads(stable(a/'capture-deliveries'/(stem+'-expected-challenge.json')))
 assert receipt['challenge']==expected['challenge']and receipt['action_sequence']==expected['action_sequence']
 raw=stable(folder/'original.png');h=hashlib.sha256(raw).hexdigest()
 assert h==receipt['image_sha256']==d['captured_sha256']and raw==stable(a/d['raw_file'])
 assert raw.startswith(b'\x89PNG\r\n\x1a\n')
 if not d['injected']:assert d['captured_sha256']==d['delivered_sha256']
 images[h]=base64.b64encode(raw).decode()
 frames.append({'capture_id':cid,'step':d['step'],'capture_index':d['capture_index'],'capture_kind':d['capture_kind'],
  'injected':d['injected'],'sha256':h,'raw_path':str(folder/'original.png'),'bytes':len(raw),
  'capture_seal_sha256':sha(folder/'seal.json'),'signed_receipt':receipt,'event_seq':event['seq']})
assert frames
print(json.dumps({'time':time.time(),'export_kind':'sealed_individual_capture_prefix_not_terminal_audit',
 'rows':[{'run_id':RUN,'attempt':str(a),'frames':frames,'controller_prefix_events':len(events),
  'controller_prefix_head':head,'controller_prefix_bytes_sha256':hashlib.sha256(b''.join(sealed_lines)).hexdigest(),
  'source_ready_sha256':sha(a/'trusted-source/ready.json'),'terminal_audit_still_required':True}],
 'images_base64':images,'new_model_GUI_calls':0,'whole_trajectory_success_claimed':False,'no_runtime_mutation':True}))
'''

def main():
    run=sys.argv[1];m=manifest();assert run in {r['run_id']for r in m['remaining_queue']}
    from control import PACKAGE
    prefix='P='+repr(m['package4090'])+'\nRUN='+repr(run)+'\nMANIFEST='+repr(sha(PACKAGE/'manifest.json'))+'\n'
    raw,operation=remote('4090',prefix+CODE,'export-sealed-per-capture-prefix-no-terminal-claim',timeout=55)
    value=json.loads(raw);root=HERE/('normal-frame-export-'+str(time.time_ns()));root.mkdir();folder=root/'images';folder.mkdir()
    for h,encoded in value.pop('images_base64').items():
        data=base64.b64decode(encoded,validate=True);assert hashlib.sha256(data).hexdigest()==h
        (folder/(h+'.png')).write_bytes(data)
    save(root/'sources.json',{'operation':str(operation),**value})
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
    print(json.dumps({'root':str(root),'seal_sha256':sha(root/'seal.json'),'unique_original_PNGs':len(list(folder.glob('*.png'))),
      'terminal_or_success_claimed':False,'new_model_GUI_calls':0}))

if __name__=='__main__':main()
