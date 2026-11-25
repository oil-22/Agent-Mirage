"""Read-only export of new public source/CPU receipts; excludes private token."""
import base64
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

stamp='1793985778592347799'
code=r'''
import base64,hashlib,json
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-source-preparation/1793985778592347799')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'receipt.json')=='d105ba2c4e0eed8f9d89cdf27663ea22413c9660c035161498064cec23c127c0'
seal=json.loads((root/'public-seal.json').read_bytes())
assert 'private.token'not in seal
for name,expected in seal.items():assert sha(root/name)==expected
files={name:base64.b64encode((root/name).read_bytes()).decode()for name in list(seal)+['public-seal.json']}
print(json.dumps({'root':str(root),'files':files,'model_HTTP_GUI_calls':0}))
'''
result=json.loads(remote(code,timeout=180,host='3090'))
target=Path(__file__).parent/'online-three-source-preparation'/stamp
target.mkdir(parents=True,exist_ok=False)
seal=json.loads(base64.b64decode(result['files']['public-seal.json']))
for name,encoded in result.pop('files').items():
    raw=base64.b64decode(encoded)
    if name!='public-seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
    with(target/name).open('xb')as f:f.write(raw)
with(target/'local-transfer.json').open('x')as f:json.dump({**result,'all_public_SHA_verified':True,'private_token_copied':False},f,indent=2)
print(json.dumps({'local':str(target),'verified_public_files':len(seal)+1,'model_HTTP_GUI_calls':0}))
