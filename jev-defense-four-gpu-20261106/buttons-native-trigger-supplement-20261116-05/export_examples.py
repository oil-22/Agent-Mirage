"""Export unmodified actual source/delivered/recovery PNGs for independent review."""
import base64
import hashlib
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import base64,hashlib,json,time
from pathlib import Path
p=Path(P);images={};rows=[]
def image(a,name):
 if name is None:return None
 raw=(a/name).read_bytes();digest=hashlib.sha256(raw).hexdigest()
 assert raw.startswith(b'\x89PNG\r\n\x1a\n')
 images[digest]=base64.b64encode(raw).decode()
 return {'sha256':digest,'remote_path':str(a/name),'bytes':len(raw)}
for a in sorted((p/'batch/runs').glob('*/attempt-*')):
 events=[];raw=(a/'controller/events.jsonl').read_bytes()
 for line in raw.splitlines(keepends=True):
  if line.endswith(b'\n'):events.append(json.loads(line))
 attacks=[v for v in events if v['kind']=='PRIVATE_capture_injection'and v['data']['injected']]
 for attack in attacks:
  d=attack['data'];current=image(a,d['raw_file']);delivered=image(a,d['delivered_file'])
  assert current['sha256']==d['captured_sha256']and(None if delivered is None else delivered['sha256'])==d['delivered_sha256']
  own_pre=[v for v in events if v['kind']=='precheck_decision'and v['data']['capture_id']==d['capture_id']]
  own_flash=[v for v in events if v['kind']=='gate_decision'and v['data']['capture_id']==d['capture_id']]
  fresh=None;fresh_event=None
  rejected=bool(own_pre)or bool(own_flash and own_flash[0]['data']['decision']=='NO')
  if rejected:
   for v in events:
    if v['seq']>attack['seq']and v['kind']=='PRIVATE_capture_injection'and v['data']['step']==d['step']and v['data']['capture_kind']=='recapture'and not v['data']['injected']:
     fresh_event=v;fresh=image(a,v['data']['raw_file']);break
  rows.append({'run_id':a.parent.name,'attack_event':attack,'precheck':own_pre,'Flash':own_flash,'raw_current':current,'delivered':delivered,'fresh_recovery':fresh,'fresh_event':fresh_event,'not_final_acceptance_without_full_audit':True})
print(json.dumps({'time':time.time(),'rows':rows,'images_base64':images,'new_model_GUI_calls':0}))
'''


def main():
    raw, operation = remote('4090', 'P=' + repr(manifest()['package4090']) + '\n' + CODE, 'export-actual-original-images')
    value = json.loads(raw)
    root = HERE / ('image-source-review-' + str(time.time_ns()))
    root.mkdir()
    folder = root / 'images'
    folder.mkdir()
    for expected, encoded in value.pop('images_base64').items():
        image = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(image).hexdigest() == expected
        (folder / (expected + '.png')).write_bytes(image)
    save(root / 'sources.json', {'operation': str(operation), **value})
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'rows': value['rows']}))


if __name__ == '__main__':
    main()
