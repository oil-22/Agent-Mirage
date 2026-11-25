import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
source='/home/researcher/jev-defense-four-gpu-20261106/failed-input-CPU-layout-audits/1793982908234148012'
code='SOURCE='+repr(source)+'\n'+'''
import base64,hashlib,json
from pathlib import Path
root=Path(SOURCE);seal=json.loads((root/'seal.json').read_bytes())
for name,expected in seal.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
print(json.dumps({name:base64.b64encode((root/name).read_bytes()).decode()for name in list(seal)+['seal.json']}))
'''
files=json.loads(remote(code,timeout=90))
dest=Path(__file__).resolve().parents[1]/'failed-input-CPU-layout-audits/1793982908234148012'
dest.mkdir(parents=True,exist_ok=False)
for name,encoded in files.items():
    path=dest/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as handle:handle.write(base64.b64decode(encoded))
seal=json.loads((dest/'seal.json').read_bytes())
for name,expected in seal.items():assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==expected
print(json.dumps({'local_receipt':str(dest/'receipt.json'),'sha256':seal['receipt.json'],'sealed_files_verified':len(seal)}))
