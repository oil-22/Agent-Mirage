"""Read-only small postexit mirror for semantic review during full tensor transfer."""
import base64,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'compact-semantic-review-source-02';O.mkdir(exist_ok=False)
REMOTE='/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-compact-four-first-attempts-02'
code='''import base64,hashlib,json,pathlib
r=pathlib.Path('''+repr(REMOTE)+''')
raw=(r/'terminal-manifest.json').read_bytes();m=json.loads(raw)
names=['exit.json','worker/input-manifest.original.json','worker/terminal.json']
for i in range(4):
 names.extend('worker/r%03d/'%i+n for n in ['raw-output.txt','result.json','evidence-packet.json'])
out={'terminal_manifest_base64':base64.b64encode(raw).decode(),'files':[]}
for n in names:
 b=(r/n).read_bytes();assert hashlib.sha256(b).hexdigest()==m[n]
 out['files'].append({'path':n,'sha256':m[n],'base64':base64.b64encode(b).decode()})
print(json.dumps(out))
'''
result=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','3090','python3','-'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
(O/'source.py').write_text(code,encoding='utf8');(O/'stderr.txt').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode(errors='replace')
v=json.loads(result.stdout);raw=base64.b64decode(v['terminal_manifest_base64']);m=json.loads(raw)
(O/'terminal-manifest.json').write_bytes(raw)
audit=json.loads((R/'gpu-compact-four-terminal-collection-02/remote-audit.json').read_bytes())
assert hashlib.sha256(raw).hexdigest()==audit['terminal_manifest_sha256']
for row in v['files']:
    p=O/row['path'];assert p.resolve().is_relative_to(O.resolve())
    b=base64.b64decode(row['base64']);assert hashlib.sha256(b).hexdigest()==row['sha256']==m[row['path']]
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(b)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(O/'receipt.json').write_text(json.dumps({'status':'selected_postexit_semantic_sources_bound_to_original_terminal_manifest','files':len(v['files']),'original_terminal_manifest_sha256':sha(O/'terminal-manifest.json'),'new_model_GUI_calls':0,'full_tensor_collection_still_separate':True},indent=2)+'\n',encoding='utf8')
(O/'seal.json').write_text(json.dumps({str(p.relative_to(O)):sha(p)for p in O.rglob('*')if p.is_file()},indent=2)+'\n',encoding='utf8')
print(json.dumps({'local':str(O),'files':len(v['files']),'seal_sha256':sha(O/'seal.json')}))
