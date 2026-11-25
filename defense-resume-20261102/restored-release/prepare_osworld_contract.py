"""Bind the actual 27B OSWorld dialect without importing old batch launchers.

This prepares an adapter contract only: no desktop, model, or evaluator calls.
"""
import ast,hashlib,json,math,re,types
from pathlib import Path
from remote import remote

HERE=Path(__file__).resolve().parent
SRC=HERE/'native-adapter-sources'/'osworld'

def node(filename,name,kind):
    tree=ast.parse((SRC/filename).read_bytes())
    for item in tree.body:
        if kind=='function' and isinstance(item,ast.FunctionDef) and item.name==name:return item
        if kind=='assign' and isinstance(item,ast.Assign) and any(isinstance(t,ast.Name)and t.id==name for t in item.targets):return item.value
    raise ValueError((filename,name))

def sha(raw):return hashlib.sha256(raw).hexdigest()

base_system=ast.literal_eval(node('run_qwen_osworld.py','SYSTEM','assign'))
gui=ast.literal_eval(node('run_qwen_osworld.py','GUI','assign'))
expr=node('run_qwen_osworld_grounding_v3.py','SYSTEM','assign')
system=eval(compile(ast.Expression(expr),'<frozen-system>','eval'),{'__builtins__':{}},{'original':types.SimpleNamespace(SYSTEM=base_system)})
system+=ast.literal_eval(node('diagnose_action_completion.py','FORMAT','assign'))
canonical=node('run_qwen_osworld_action_v4.py','canonical_action','function')
convert=node('run_qwen_osworld_grounding_v3.py','convert','function')
namespace={'ast':ast,'re':re,'math':math,'original':types.SimpleNamespace(GUI=gui)}
exec(compile(ast.Module(body=[canonical,convert],type_ignores=[]),'<frozen-native-parser>','exec'),namespace)

# Geometric calibration is independent of task answers and GUI execution.
text='Evidence: current visible target.\n```python\nclick(x=250, y=750)\n```'
code=namespace['canonical_action'](text)
actual=namespace['convert'](code,1920,1080)
assert actual=='pyautogui.click(x=480, y=810)',actual
assert namespace['canonical_action']('WAIT')=='WAIT'
assert namespace['canonical_action']('```python\npyautogui.FAIL()\n```')=='FAIL'
try:namespace['canonical_action']('```python\n__import__("os").system("anything")\n```')
except ValueError:pass
else:raise AssertionError('Native whitelist missing')

remote_code=r'''
import pathlib,json,hashlib
base=pathlib.Path('/data/researcher/osworld-qwen27-2026-10-13')
sources=sorted((base/'results-action-v5/runs').glob('*/*/*/requests/001.json'))
if not sources:raise RuntimeError('No archived native v5 request; do not guess system')
p=sources[0];raw=p.read_bytes();body=json.loads(raw)
print(json.dumps({'source':str(p),'request_sha256':hashlib.sha256(raw).hexdigest(),
 'system':body['messages'][0]['content'],'parameters':{k:v for k,v in body.items()if k!='messages'}}))
'''
reference=json.loads(remote(remote_code,host='4090'))
assert system==reference['system'],'Native system mismatch: adapter cannot launch'
assert reference['parameters']['temperature']==0 and reference['parameters']['max_tokens']==2048
provenance=json.loads((SRC/'provenance.json').read_text())
result={'scope':'Native OSWorld adapter preparation only; no live defense run',
 'native_system_matches_actual_archive':True,'system_sha256':sha(system.encode()),
 'sources':provenance,'archived_reference':reference,
 'parser_ast_sha256':sha(ast.dump(canonical,include_attributes=False).encode()),
 'conversion_ast_sha256':sha(ast.dump(convert,include_attributes=False).encode()),
 'calibration':{'normalized':[250,750],'native':[480,810],'image':[1920,1080],'actual_code':actual,
                'wait_preserved':True,'fail_preserved':True,'arbitrary_code_rejected':True},
 'desktop_actions':0,'model_calls':0,'official_evaluations':0,'ready_for_online':False,
 'remaining':['Bind original same-live capture and button mask','Environment ownership and lock preflight',
              'Bind actual model request template including thinking setting','Native evaluator transport and isolated VM preflight',
              'Independent live recovery diagnostic before formal twenty configurations']}
out=HERE/'osworld-native-contract.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'written':str(out),'system_matches':True,'calibration_passed':True,'ready_for_online':False}))
