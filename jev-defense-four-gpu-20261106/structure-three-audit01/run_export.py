import base64,hashlib,io,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
here=Path(__file__).resolve().parent
source=(here/'export_review_remote.py').read_bytes();expected=hashlib.sha256(source).hexdigest()
code='''import base64,hashlib,pathlib,subprocess,time,sys
raw=base64.b64decode(SOURCE);assert hashlib.sha256(raw).hexdigest()==EXPECTED
root=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/three-review-export-source-'+str(time.time_ns()));root.mkdir(mode=0o700)
path=root/'export_review_remote.py';path.write_bytes(raw)
r=subprocess.run(['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-B',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if r.returncode:
 (root/'failure.stdout').write_bytes(r.stdout);(root/'failure.stderr').write_bytes(r.stderr)
 sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)
sys.stdout.buffer.write(r.stdout)
'''
result=json.loads(remote('SOURCE='+repr(base64.b64encode(source).decode())+'\nEXPECTED='+repr(expected)+'\n'+code,timeout=180,host='4090'))
out=here/'legal-review-export';out.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(result.pop('zip_base64'))))as z:
    for name in z.namelist():
        p=(out/name).resolve();assert p.is_relative_to(out.resolve())
    z.extractall(out)
seal=json.loads((out/'seal.json').read_bytes())
for name,h in seal.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h,name
assert hashlib.sha256((out/'seal.json').read_bytes()).hexdigest()==result['seal_sha256']
assert hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest()==result['receipt_sha256']
(here/'export-transfer.json').write_text(json.dumps({**result,'all_files_SHA_verified':True},indent=2),encoding='utf8')
print(json.dumps({**result,'local':str(out),'verified_files':len(seal)+1}))
