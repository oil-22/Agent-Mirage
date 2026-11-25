import base64,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
code=r'''
import base64,hashlib,json
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/online-submit-control-repair/1793986405735234912')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'receipt.json')=='f8d958d006cb6fd1626a3ddd5a540cfc02161bbf894254fcef42dbc97572598f'
seal=json.loads((root/'seal.json').read_bytes())
for name,expected in seal.items():assert sha(root/name)==expected
assert not any('private.token'in name for name in seal)
print(json.dumps({'files':{name:base64.b64encode((root/name).read_bytes()).decode()for name in list(seal)+['seal.json']}}))
'''
value=json.loads(remote(code,timeout=180,host='3090'))
root=Path(__file__).parent/'submit-control-evidence/1793986405735234912'
root.mkdir(parents=True,exist_ok=False)
seal=json.loads(base64.b64decode(value['files']['seal.json']))
for name,encoded in value['files'].items():
    raw=base64.b64decode(encoded)
    if name!='seal.json':assert hashlib.sha256(raw).hexdigest()==seal[name]
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as f:f.write(raw)
print(json.dumps({'local':str(root),'files_SHA_verified':len(seal)+1,'private_tokens_copied':False,'model_HTTP_GUI_calls':0}))
