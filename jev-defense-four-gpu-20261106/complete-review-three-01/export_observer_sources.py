"""Independent source-first observer image review; replies stay in a separate file."""
import base64,hashlib,io,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

CODE=r'''
import base64,hashlib,io,json,struct,zipfile
from pathlib import Path
p=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761/events.jsonl')
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=p.read_bytes();assert sha(raw)=='0e62fa3a2a75618e75a0160a6aa96d2e1e269a0d31cc2522588d8829fabec085'
images={};manifest=[];responses=[];pending=None
for line in raw.splitlines():
 row=json.loads(line)
 if row['kind']=='actual_observer_wire':
  d=row['data'];envelope=d['body'];payload=envelope['payload']
  image=base64.b64decode(payload['image_base64'],validate=True);key=sha(image);assert key==payload['image_sha256']
  images[key]=image
  pending={'index':len(manifest)+1,'request_event_seq':row['seq'],'request_event_sha256':row['sha256'],'request_wire_sha256':sha(d['wire_utf8'].encode()),'image_sha256':key,'image_size':list(struct.unpack('>II',image[16:24])),'observation_id':payload['provenance']['observation_id'],'payload_keys':list(payload),'fixed_state':payload['state'],'fixed_questions':payload['questions']}
 elif row['kind']=='actual_observer_wire_reply':
  assert pending is not None;d=row['data'];wire=base64.b64decode(d['raw_base64'],validate=True);assert sha(wire)==d['raw_sha256']
  pending.update(response_event_seq=row['seq'],response_event_sha256=row['sha256'],response_raw_sha256=sha(wire))
  responses.append({'index':pending['index'],'response':json.loads(wire)})
  manifest.append(pending);pending=None
assert len(manifest)==len(responses)==20 and pending is None
files={'source-manifest.json':json.dumps({'event_file_sha256':sha(raw),'image_count':len(images),'forward_count':20,'images_and_original_input_contract_only':manifest},ensure_ascii=False,indent=2).encode(),'replies.json':json.dumps(responses,ensure_ascii=False,indent=2).encode()}
for key,image in images.items():files['images/'+key+'.png']=image
files['seal.json']=json.dumps({k:sha(v)for k,v in files.items()},indent=2).encode()
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
 for k,v in files.items():z.writestr(k,v)
print(json.dumps({'zip_base64':base64.b64encode(buf.getvalue()).decode(),'seal_sha256':sha(files['seal.json']),'image_count':len(images),'forward_count':20}))
'''

if __name__=='__main__':
    result=json.loads(remote(CODE,timeout=90,host='4090'))
    out=Path(__file__).parent/'observer-image-review-01';out.mkdir(exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(result.pop('zip_base64'))))as z:
        for name in z.namelist():assert(out/name).resolve().is_relative_to(out.resolve())
        z.extractall(out)
    seal=json.loads((out/'seal.json').read_bytes())
    for name,expected in seal.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==expected
    assert hashlib.sha256((out/'seal.json').read_bytes()).hexdigest()==result['seal_sha256']
    (out/'export-source.py').write_bytes(Path(__file__).read_bytes())
    (out/'delivery.json').write_text(json.dumps({**result,'all_original_image_SHA_verified':True,'replies_not_read_for_initial_visual_labels':True},indent=2),encoding='utf8')
    print(json.dumps({'local':str(out),**result}))
