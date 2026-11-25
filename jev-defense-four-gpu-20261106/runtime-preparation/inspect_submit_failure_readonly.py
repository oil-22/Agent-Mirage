import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
print(remote(r'''
import json,hashlib
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-source-preparation/1793985778592347799')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in root.iterdir()if p.is_file()and p.name!='private.token'],
 'command':json.loads((root/'holder-command.proposed.json').read_bytes()),
 'finalization':json.loads((root/'reviewed-finalization.json').read_bytes())}))
''',timeout=180,host='3090'))
