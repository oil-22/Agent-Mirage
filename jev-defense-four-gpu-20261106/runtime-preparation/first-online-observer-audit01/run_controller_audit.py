import base64,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
get=r'''
import base64,json
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/first-online-observer-engineering/1793987640839997700')
print(json.dumps({'files':{str(p.relative_to(root)):base64.b64encode(p.read_bytes()).decode()for p in root.rglob('*')if p.is_file()and'auditor-source'not in p.parts}}))
'''
files=json.loads(remote(get,timeout=180,host='3090'))['files']
here=Path(__file__).resolve().parent
source=(here/'audit_controller_remote.py').read_text(encoding='utf8')
print(remote('PUBLIC_SERVICE='+repr(files)+'\n'+source,timeout=180,host='4090'))
