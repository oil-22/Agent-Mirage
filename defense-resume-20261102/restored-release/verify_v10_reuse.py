"""Bind unchanged actor/capacity controls to v10 without redoing inference."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;new=json.loads((here/'v10-service-launch.json').read_text());old=json.loads((here/'v9-service-launch.json').read_text())
capacity=json.loads((here/'v9-capacity-progress.json').read_text());assert capacity['summary']['passed']
code=r'''import pathlib,json,hashlib,types,ast
new=pathlib.Path(NEW);old=pathlib.Path(OLD);release=pathlib.Path(RELEASE);prior=pathlib.Path(PRIOR)
assert json.loads((new/'status.json').read_text())['phase']=='ready'
assert(new/'runtime.json').read_bytes()==(old/'runtime.json').read_bytes()
def method(path,name):return next(ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.FunctionDef)and n.name==name)
for name in ['generate','judge']:assert method(release/'defense/qwen_backend.py',name)==method(prior/'defense/qwen_backend.py',name)
for name in ['inference_server.py','defense/http_backend.py','native-vwa-request.json','plan80.json']:
 assert(release/name).read_bytes()==(prior/name).read_bytes()
oldns={};newns={};exec((prior/'defense/schema.py').read_text(),oldns);exec((release/'defense/schema.py').read_text(),newns)
source=pathlib.Path(CAPREQUEST);body=json.loads((source/'request.json').read_text());v=body['view']
view=types.SimpleNamespace(observation_id=v['observation_id'],messages=v['messages'],images=v['images'])
schema=newns['judge_schema'](view,body['candidate']);assert schema==oldns['judge_schema'](view,body['candidate'])
generation=json.loads((source/'generation.json').read_text());assert generation['verifier_grammar']['schema']==schema
print(json.dumps({'passed':True,'runtime_sha256':hashlib.sha256((new/'runtime.json').read_bytes()).hexdigest(),'generate_and_judge_ast_identical_to_v9':True,'original_capacity_schema_exact':True,'capacity_request_sha256':hashlib.sha256((source/'request.json').read_bytes()).hexdigest(),'scope':'Reuses actual v9 native token equivalence and capacity controls with identical runtime, methods and original nonhistory schema; new history protocol still requires new inference'}))
'''.replace('NEW',repr(new['root'])).replace('OLD',repr(old['root'])).replace('RELEASE',repr(new['release'])).replace('PRIOR',repr(old['release'])).replace('CAPREQUEST',repr(capacity['summary']['cases'][1]['new_receipt']))
data=json.loads(remote(code));data['capacity_summary_sha256']=capacity['summary_sha256'];data['capacity_source']=json.loads((here/'v9-capacity-replay-launch.json').read_text())['root']
(here/'v10-service-validation.json').write_text(json.dumps(data,indent=2));print(json.dumps(data))
