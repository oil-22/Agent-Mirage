"""Metadata-only linked correction; no model or GUI calls."""
import base64,hashlib,io,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
here=Path(__file__).parent
original=here.parent/'structure-three-audit01/export_review_remote.py'
source=original.read_text(encoding='utf-8')
old="data['body'].get('payload',{}).get('operation')=='judge'"
new="data['body'].get('operation')=='judge'"
assert source.count(old)==1
source=source.replace(old,new)
needle="    for i,value in enumerate(judges,1):save(ROOT/'review/judges'/f'{i:03}.json',value)"
assert needle in source
source=source.replace(needle,"    assert all('actual_wire_sha256' in v and 'actual_native_payload' in v for v in judges)\n"+needle)
out=here/'judge-legal-projection-linked02'
assert not out.exists()
code="SOURCE="+repr(base64.b64encode(source.encode()).decode())+"\n"+r'''
import base64,hashlib,pathlib,subprocess,time,sys
raw=base64.b64decode(SOURCE)
root=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/root-judge-export-linked02-'+str(time.time_ns()));root.mkdir(mode=0o700)
path=root/'export_review_remote.py';path.write_bytes(raw)
r=subprocess.run(['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-B',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if r.returncode:
 (root/'failure.stdout').write_bytes(r.stdout);(root/'failure.stderr').write_bytes(r.stderr)
 sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)
sys.stdout.buffer.write(r.stdout)
'''
if __name__=='__main__':
 result=json.loads(remote(code,host='4090',timeout=180))
 out.mkdir(exist_ok=False)
 with zipfile.ZipFile(io.BytesIO(base64.b64decode(result.pop('zip_base64'))))as z:
  for n in z.namelist():assert(out/n).resolve().is_relative_to(out.resolve())
  z.extractall(out)
 seal=json.loads((out/'seal.json').read_bytes())
 for n,h in seal.items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h,n
 assert hashlib.sha256((out/'seal.json').read_bytes()).hexdigest()==result['seal_sha256']
 assert hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest()==result['receipt_sha256']
 result.update(local=str(out),all_files_SHA_verified=True,original_export_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),metadata_only_correction='Use outer envelope.operation, not native payload.operation; assert all73 have actual wire and native payload.')
 (out/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
