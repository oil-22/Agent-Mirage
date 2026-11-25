import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
source = Path(r'D:\MultiModel\jev-defense-four-gpu-20261106\gui-before-begin-unspent-proof\1793979448527081100')
files = {path.relative_to(source).as_posix():base64.b64encode(path.read_bytes()).decode()
         for path in source.rglob('*') if path.is_file()}
target = '/data/researcher/jev-defense-four-gpu-20261106/gui-before-begin-unspent-proof/1793979448527081100'
code = '''import base64,hashlib,json
from pathlib import Path
root=Path(TARGET)
root.mkdir(parents=True,exist_ok=False)
for name,encoded in FILES.items():
 path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as handle:handle.write(base64.b64decode(encoded))
seal=json.loads((root/'seal.json').read_bytes())
for name,expected in seal.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
assert hashlib.sha256((root/'receipt.json').read_bytes()).hexdigest()=='43b7a3828cd0ede6038da08ce53bcec631d43723b0b1ad730602418bab6dc9f2'
assert hashlib.sha256((root/'seal.json').read_bytes()).hexdigest()=='0a61927a508b1e2cdf62312518212785012395ee469a010d5a5efbf89513ba6c'
print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':hashlib.sha256((root/'receipt.json').read_bytes()).hexdigest(),'sealed_files':len(seal),'model_HTTP_GUI_calls':0}))
'''
print(remote('TARGET='+repr(target)+'\nFILES='+repr(files)+'\n'+code, host='4090', timeout=90))
