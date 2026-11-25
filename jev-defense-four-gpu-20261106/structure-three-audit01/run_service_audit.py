import ast,base64,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
B=Path(__file__).resolve().parents[1];H=Path(__file__).resolve().parent
A=B/'policy-preparation/image-observer-policy/gui-migration-three-linked02/terminal-auditor/audit_gui_terminals.py'
V=B/'policy-preparation/image-observer-policy/gui-migration-three-linked02/release/image_observer.py'
P=B/'flash-preparation/source-fixed/src/pplx_decider/protocol.py'
S=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def selected(path,names):
    source=path.read_text(encoding='utf8');tree=ast.parse(source)
    nodes={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    assert set(names)<=set(nodes)
    return '\n\n'.join(ast.get_source_segment(source,nodes[name])for name in names)
values={n.targets[0].id:ast.literal_eval(n.value)for n in ast.parse(V.read_text(encoding='utf8')).body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in('STATE','QUESTIONS','MODEL','REVISION')}
lib='from __future__ import annotations\nimport copy\n'+ '\n'.join(k+'='+repr(v)for k,v in values.items())+'\n'
lib+=selected(A,['AuditError','sha','canonical','require','read','under','manifest','image_raw','public_from_judge','generation_messages','native_forward','service_chain'])+'\n'
lib+=selected(V,['valid_answer'])+'\n'+selected(P,['options','answer'])
compile(lib,'native-library.py','exec')
source=(H/'service_audit_remote.py').read_text(encoding='utf8')
source='LIB_CODE='+repr(lib)+'\nAUDITOR_SHA='+repr(S(A))+'\nOBSERVER_SHA='+repr(S(V))+'\nPROTOCOL_SHA='+repr(S(P))+'\n'+source
source=source.replace('import base64,hashlib,io,json,math,os,struct,time','import base64,copy,hashlib,io,json,math,os,struct,time',1)
compile(source,'service_audit_remote.py','exec')
code='''import base64,hashlib,pathlib,subprocess,sys,time
raw=base64.b64decode(SOURCE);root=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/three-service-audit-source-'+str(time.time_ns()));root.mkdir(mode=0o700)
p=root/'service_audit_remote.py';p.write_bytes(raw)
r=subprocess.run(['/home/researcher/jev-defense-four-gpu-20261106/flash-preparation/env-flash-01/bin/python','-B',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(root/'stdout.txt').write_bytes(r.stdout);(root/'stderr.txt').write_bytes(r.stderr)
if r.returncode:sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)
sys.stdout.buffer.write(r.stdout)
'''
result=json.loads(remote('SOURCE='+repr(base64.b64encode(source.encode()).decode())+'\n'+code,timeout=300,host='3090'))
out=H/('service-audit-public-'+str(time.time_ns()));out.mkdir(exist_ok=False)
files=result.pop('files')
for name,b64 in files.items():
    assert Path(name).name==name
    (out/name).write_bytes(base64.b64decode(b64))
for name,h in json.loads((out/'seal.json').read_bytes()).items():assert S(out/name)==h,name
assert S(out/'receipt.json')==result['receipt_sha256']and S(out/'seal.json')==result['seal_sha256']
(out.parent/(out.name+'-transfer.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({**result,'local':str(out)}))
