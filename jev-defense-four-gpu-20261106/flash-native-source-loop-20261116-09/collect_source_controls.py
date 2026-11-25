"""Audit new real-browser captures/faults and export originals for image review."""
import base64
import json
import time
from pathlib import Path
from remote_util import HERE, remote, save, sha


def main():
    pp = json.loads((HERE / 'CPU-source-current.json').read_bytes()); src = Path(pp['root'])
    assert sha(src / 'seal.json') == pp['seal_sha256']
    remote_root = pp['remote_root']
    code = 'ROOT=' + repr(remote_root) + '\n' + r'''
import base64,hashlib,json,os,time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
p=Path(ROOT)
for n,h in json.loads((p/'seal.json').read_bytes()).items():assert sha(p/n)==h,n
processes=[];signed=0;faults=0
for src in[p/'live-controls/fixture/trusted-source',p/'live-controls/native-source']:
 ready=json.loads((src/'ready.json').read_bytes());terminal=json.loads((src/'terminal.json').read_bytes());head='0'*64
 saved=ready['identity'];proc=Path('/proc',str(saved['pid']));actual=None
 if proc.exists():
  st=(proc/'stat').read_text().rsplit(')',1)[1].split();actual={'uid':proc.stat().st_uid,'start_ticks':st[19],'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'state':st[0]}
  assert actual['state']in['X','Z']or any(actual[k]!=saved[k]for k in['uid','command','start_ticks'])
 processes.append({'saved':saved,'actual':actual,'original_exited':True})
 key=Ed25519PublicKey.from_public_bytes(bytes.fromhex(ready['public_key']));captures={}
 for line in(src/'events.jsonl').read_bytes().splitlines():
  event=json.loads(line);h=event.pop('sha256');assert event['previous']==head and hashlib.sha256(canonical(event)).hexdigest()==h;head=h
  if event['kind']=='actual_native_capture_signed':
   r=event['data']['receipt'];body={k:v for k,v in r.items()if k!='signature'};key.verify(bytes.fromhex(r['signature']),canonical(body));folder=src/('capture-'+r['capture_id']);assert sha(folder/'original.png')==r['image_sha256'];captures[r['capture_id']]=r;signed+=1
  if event['kind']=='PRIVATE_unsigned_native_fault_rendered':
   d=event['data'];r=captures[d['preceding_capture_id']];assert not d['signature_issued']and r['image_sha256']==d['preceding_signed_image_sha256'];assert sha(src/('unsigned-fault-'+r['capture_id'])/'delivered.png')==d['delivered_sha256'];assert d['CSS_removed_before_gate'];faults+=1
 assert head==terminal['journal_head']and terminal['signed_captures']==len(captures)and not terminal['private_key_exported']
names=['fixture/normal-before.png','fixture/masked-unsigned.png','fixture/normal-recapture.png','fixture/legitimate-lone-button.png','real-native-normal.png','real-native-mask.png','real-native-recapture.png']
images={n:{'sha256':sha(p/'live-controls'/n),'b64':base64.b64encode((p/'live-controls'/n).read_bytes()).decode()}for n in names}
print(json.dumps({'signed_captures':signed,'unsigned_faults':faults,'source_chains_signatures_and_exit_verified':True,'processes':processes,'images':images,'new_model_calls':0}))
'''
    raw, operation = remote('4090', code, 'new-source-controls-original-image-and-signature-audit', timeout=90)
    value = json.loads(raw)
    root = HERE / ('source-review-' + str(time.time_ns())); root.mkdir()
    rows = []
    for name, image in value.pop('images').items():
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(base64.b64decode(image['b64'], validate=True))
        assert sha(target) == image['sha256']; rows.append({'file': name, 'sha256': sha(target)})
    save(root / 'audit.json', {'operation': str(operation), **value, 'images': rows})
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'source-review-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), **value, 'images': rows}))


if __name__ == '__main__':
    main()
