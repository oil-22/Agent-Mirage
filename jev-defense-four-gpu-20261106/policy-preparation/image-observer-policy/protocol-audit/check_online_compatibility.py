"""CPU protocol check executing only actual server health method, never main/load."""
import ast,copy,hashlib,json,sys,tempfile,traceback
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch
from defense.http_backend import RemoteQwen

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
source=ROOT/'runtime-preparation/gui-linked-01/online_service.py'
raw=source.read_bytes();tree=ast.parse(raw)
method=next(n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name=='do_GET')
health=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='health_result')
module=ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(health),ast.ClassDef(name='ActualHealthOnly',bases=[],keywords=[],
    body=[copy.deepcopy(method)],decorator_list=[])],type_ignores=[]))
with tempfile.TemporaryDirectory()as temp:
    state=Path(temp)/'online-state.json';state.write_text('{"phase":"ready"}')
    resources={'verified_owned':True,'compute':[],'actual_allowed_pids':[11,22]}
    for role in ['primary','pplx_flash']:
        (Path(temp)/role).mkdir();(Path(temp)/role/'ready.json').write_text('{}')
    env={'json':json,'traceback':traceback,'resource_admission':lambda *_:resources,
         'lease':{},'group':Path(temp),'commands':{},'FLASH':'pplx_flash',
         'a':type('A',(),{'role':'primary'})(), 'state_path':state}
    exec(compile(module,str(source),'exec'),env)
    cls=env['ActualHealthOnly']
    class Response:
        def __init__(self,code,value):self.status_code,self.value=code,value
        def raise_for_status(self):
            if self.status_code>=400:raise RuntimeError('HTTP '+str(self.status_code))
        def json(self):return self.value
    def handler(path,authorized=True):
        obj=cls();obj.path=path;obj.authenticated=lambda:authorized;obj.reply=lambda c,v:Response(c,v)
        return obj.do_GET()
    token=Path(temp)/'token';token.write_text('synthetic-only-token')
    native=RemoteQwen('http://127.0.0.1:18888',token)
    with patch('requests.get',side_effect=lambda url,**kwargs:handler(urlsplit(url).path or'/')):
        out=native.health();assert out['phase']=='ready_gui'and out['stage']=='online_ready'
    assert handler('/health').json()['phase']=='ready_gui'
    assert handler('/',False).status_code==403
    env['resource_admission']=lambda *_:(_ for _ in ()).throw(RuntimeError('synthetic foreign-resource conflict'))
    assert handler('/').status_code==503
receipt={'CPU_protocol_checks_passed':4,'scope':'actual source-derived do_GET and inherited original RemoteQwen.health only; no server main/engine/browser invoked',
    'source_sha256':hashlib.sha256(raw).hexdigest(),'native_client_GET_root_compatible':True,
    'health_alias_compatible':True,'phase_ready_gui_compatible':True,
    'authorization_and_resource_refusal_preserved':True,
    'five_field_inference_and_lifecycle_schema_source_reviewed':True,
    'actual_deployment_ready_claim':False,'new_model_GPU_GUI_calls':0}
dest=BASE/'compatibility-receipt.json'
with dest.open('x',encoding='utf8')as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
print(json.dumps(receipt,ensure_ascii=False))
