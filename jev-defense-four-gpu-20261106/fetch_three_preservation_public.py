"""Read only public preservation receipts; no snapshots/private contents exported."""
import base64,concurrent.futures,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE=Path(__file__).resolve().parent
ROOTS={
 '3090':('/home/researcher/jev-defense-four-gpu-20261106/three-terminal-prestop-preservation/1794040105015962100','16fb3e744dcf373932a3ba44c4fc690284049f150e95505816a974758e6be386','47fd5fa7c89ec0193070ec8520378422bf1069142424ad77800bde7ecc35b3a9'),
 '4090':('/data/researcher/jev-defense-four-gpu-20261106/three-terminal-prestop-preservation/1794040037028433500','7187f5818b3541a82fc8cd0f3b15abcf27d9fb555206bfb207b1bda033d37256','795b475a7345139a64000fbee52196ecb0288b67ef95556690c52d8c532dd05b')}
CODE=r'''
import base64,hashlib,json
from pathlib import Path
p=Path(ROOT);sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert sha(p/'receipt.json')==RECEIPT and sha(p/'preservation-seal.json')==SEAL
names=('receipt.json','preservation-seal.json','actual-idle-proof.json','source-manifests-before.json')
print(json.dumps({'root':str(p),'files':{n:{'sha256':sha(p/n),'base64':base64.b64encode((p/n).read_bytes()).decode()}for n in names},'private_snapshot_content_exported':False}))
'''
def fetch(host,out):
 root,receipt,seal=ROOTS[host]
 code='ROOT='+repr(root)+'\nRECEIPT='+repr(receipt)+'\nSEAL='+repr(seal)+'\n'+CODE
 value=json.loads(remote(code,timeout=120,host=host));target=out/host;target.mkdir()
 for name,row in value.pop('files').items():
  raw=base64.b64decode(row['base64']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
  with(target/name).open('xb')as f:f.write(raw)
 return{'host':host,'remote_root':root,'receipt_sha256':receipt,'seal_sha256':seal,'local_root':str(target),'public_only':True}
if __name__=='__main__':
 out=BASE/'three-terminal-prestop-public'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
   fs=[pool.submit(fetch,h,out)for h in ROOTS]
   rows=[f.result()for f in fs]
  (out/'receipt.json').write_text(json.dumps({'remote_public_receipts':rows,'model_GUI_health_signals':0},indent=2),encoding='utf8')
  print(json.dumps({'local_root':str(out),'rows':rows}))
 finally:(out/'seal.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
