"""Seal/audit a completed attempt, mirror public artifacts without raw tensors."""
from pathlib import Path
import base64
import hashlib
import io
import json
import time
import zipfile
from ops import HERE,ROOT,remote,save,sha

def main():
    code='ROOT='+repr(ROOT)+'\n'+r'''
from pathlib import Path
import base64,hashlib,io,json,zipfile
r=Path(ROOT);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((r/'worker/terminal.json').read_bytes());assert t['status']=='completed'
e=json.loads((r/'exit.json').read_bytes());assert e['worker_exit_code']==e['launcher_exit_code']==0
for n in ['launcher-process.json','worker/process.json']:
 v=json.loads((r/n).read_bytes());assert not Path('/proc',str(v['pid'])).exists()
manifest=json.loads((r/'terminal-manifest.json').read_bytes())
for n,h in manifest.items():assert sha(r/n)==h,n
cases=[]
for folder in list(sorted((r/'worker/auxiliary').iterdir())):
 for n,h in json.loads((folder/'seal.json').read_bytes()).items():assert sha(folder/n)==h,n
 prepared=json.loads((folder/'prepared.json').read_bytes());forward=json.loads((folder/'first-forward.json').read_bytes())
 assert set(prepared)==set(forward)
 for name,row in prepared.items():assert all(row[k]==forward[name][k]for k in ['shape','dtype','bytes','sha256']),name
 actual=json.loads((folder/'actual-generation.json').read_bytes());cfg=json.loads((folder/'effective-generation.json').read_bytes())
 mask=json.loads((folder/'actual-mask-steps.json').read_bytes())
 assert mask['all_actual_selected_tokens_allowed'] and len(mask['steps'])==len(actual['output_ids'])
 assert all(s['selected_allowed']and s['selected_id']==t for s,t in zip(mask['steps'],actual['output_ids']))
 response=json.loads((folder/'response.json').read_bytes())
 assert response['strict_native_UTF8_roundtrip']
 raw_bytes=(folder/'generated-raw-utf8.bin').read_bytes()
 assert raw_bytes.decode('utf8')==response['raw_output']==(folder/'raw-output.txt').read_text()
 assert response['image_sha256']==sha(folder/'original.png')
 eos=cfg['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
 assert actual['natural_EOS']==bool(actual['output_ids']and actual['output_ids'][-1]in eos)
 cases.append({'folder':str(folder.relative_to(r)),'input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens'],'EOS':actual['natural_EOS'],'actual_forward_calls':actual['actual_forward_calls'],'prepared_first_forward_identical':True})
event=r/'worker/journal/events.jsonl';prev='0'*64;count=0
for line in event.read_bytes().splitlines():
 v=json.loads(line);h=v.pop('sha256');assert v['seq']==count and v['previous']==prev and hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h
 prev=h;count+=1
audit={'terminal_files_full_SHA_verified':len(manifest),'terminal_manifest_sha256':sha(r/'terminal-manifest.json'),'cases':cases,'chain':{'events':count,'head':prev},'all_inference_processes_exited':True,'raw_tensor_bytes_remain_remote_under_terminal_seal':True,'new_model_calls':0}
blob=io.BytesIO();kept=[]
with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED)as z:
 for p in sorted(r.rglob('*')):
  if not p.is_file():continue
  # Numeric tensor dumps use .bin; public metadata/IDs/images/replies/journal stay.
  if p.suffix in {'.bin','.tensor','.pt','.safetensors'}:continue
  name=p.relative_to(r).as_posix();z.writestr(name,p.read_bytes());kept.append(name)
print(json.dumps({'audit':audit,'archive_base64':base64.b64encode(blob.getvalue()).decode(),'public_files':kept,'archive_sha256':hashlib.sha256(blob.getvalue()).hexdigest()}))
'''
    raw,op=remote('3090',code,'full-terminal-SHA-collection',timeout=180)
    data=json.loads(raw);root=HERE/'terminal-collection'/str(time.time_ns());root.mkdir(parents=True)
    archive=base64.b64decode(data['archive_base64']);assert hashlib.sha256(archive).hexdigest()==data['archive_sha256']
    (root/'public.zip').write_bytes(archive)
    dest=root/'original';dest.mkdir()
    with zipfile.ZipFile(io.BytesIO(archive))as z:
        for n in z.namelist():assert(dest/n).resolve().is_relative_to(dest.resolve())
        z.extractall(dest)
    manifest=json.loads((dest/'terminal-manifest.json').read_bytes())
    for n in data['public_files']:
        if n in manifest:assert sha(dest/n)==manifest[n],n
    save(root/'audit.json',data['audit']);save(root/'collection.json',{'operation':str(op),'public_files':len(data['public_files']),'public_archive_sha256':data['archive_sha256'],'audit_sha256':sha(root/'audit.json'),'raw_tensor_local_mirror_claim':False})
    print(json.dumps({'root':str(root),'audit':data['audit'],'public_files':len(data['public_files'])}))

if __name__=='__main__':main()
