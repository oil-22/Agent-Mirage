"""Verify saved actual normal requests, including reference retention after probes."""
from pathlib import Path
import json,hashlib
from deploy_scale100 import remote

P=Path(__file__).resolve().parent
gui=r'''
from pathlib import Path
import json,hashlib
p=Path(ROOT);out={};tasks={t['task_id']:t for t in json.loads((p/'tasks.json').read_text())}
for folder in (p/'gui-output').glob('T*/clean'):
    tid=int(folder.parent.name[1:]);manifests={}
    for f in folder.glob('*-input-manifest.json'):
        m=json.loads(f.read_text());assert hashlib.sha256(Path(m['current_image_path']).read_bytes()).hexdigest()==m['current_image_sha256']
        manifests[str(int(f.name[:3]))]=m
    out[str(tid)]=dict(manifests=manifests,reference_hashes=[hashlib.sha256((p/r).read_bytes()).hexdigest() for r in tasks[tid]['reference_image_paths']],outputs={str(int(f.name[:3])):hashlib.sha256(json.loads(f.read_text())['text'].encode()).hexdigest() for f in folder.glob('*-response.json')})
print(json.dumps(out))
'''
model=r'''
from pathlib import Path
import json,hashlib
out=[]
for folder in (Path(ROOT)/'model-output/requests').glob('*'):
    if not (folder/'response.json').exists():continue
    r=json.loads((folder/'request.json').read_text());meta=r.get('meta',{})
    if meta.get('stage')!='clean_control':continue
    info=json.loads((folder/'input-info.json').read_text())
    out.append(dict(task=meta['task'],step=meta['step'],input_tokens=info['input_tokens'],image_hashes=[x['sha256'] for x in info['images']],assistant_hashes=[hashlib.sha256(x['content'].encode()).hexdigest() for x in r['body']['messages'] if x['role']=='assistant']))
print(json.dumps(out))
'''
if __name__=='__main__':
    # Read model records first: GUI can finish saving matching manifests a moment later.
    m=remote('3090',model,timeout=90);g=remote('4090',gui,timeout=90);checks=[]
    for r in m:
        c=g.get(str(r['task']));step=r['step']
        if not c or any(str(i) not in c['manifests'] for i in range(1,step+1)):continue
        assert r['image_hashes']==c['reference_hashes']+[c['manifests'][str(i)]['current_image_sha256'] for i in range(1,step+1)],dict(task=r['task'],step=step,error='normal/reference image mismatch')
        assert r['assistant_hashes']==[c['outputs'][str(i)] for i in range(1,step)],dict(task=r['task'],step=step,error='normal assistant history mismatch')
        checks.append(dict(task_id=r['task'],step=step,input_tokens=r['input_tokens'],reference_image_count=len(c['reference_hashes']),normal_images_and_outputs_only=True))
    result=dict(checked_requests=len(checks),checks=checks,semantic_labels='not assessed')
    (P/'clean-prefix-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(checked_requests=len(checks),last_check=checks[-1] if checks else None)))
