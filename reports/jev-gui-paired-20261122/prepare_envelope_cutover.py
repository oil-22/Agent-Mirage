"""Build a sealed, independent runtime for only the unstarted paired suffix."""
import ast
import json
import secrets
import sys
import time
from pathlib import Path

import control
from action_envelope import VERSION
from prepare import HERE, edit, read, save, sha
from repair_handoff import REPAIR


def freeze():
    ptr = REPAIR / 'linked-current.json'
    assert not ptr.exists()
    offline = read(REPAIR / 'offline-qualification.json')
    assert offline['status']=='passed' and offline['adapter_sha256']==sha(HERE/'action_envelope.py')
    original = read(HERE / 'frozen-current.json')
    parent = Path(original['runtime'])
    m=read(parent/'manifest.json')
    assert sha(parent/'manifest.json')==original['manifest_sha256'] and sha(parent/'plan.json')==original['plan_sha256']
    assert all(sha(parent/name)==h for name,h in m['files'].items())
    armed=read(REPAIR/'drain-armed.json')['result']['job']
    n=armed['prefix']
    full=read(parent/'plan.json')
    assert 0<n<len(full['queue']) and n%2==0 and full['queue'][n-1]==armed['target']
    assert armed['manifest']==original['manifest_sha256'] and armed['plan_sha256']==original['plan_sha256']
    assert m['files']['native-parser-source.py']==offline['native_parser_sha256']
    case='paper-paired-action-envelope-v2-'+str(time.time_ns())
    root=REPAIR/case
    p=root/'runtime';p.mkdir(parents=True,exist_ok=False)
    for name in m['files']:
        dest=p/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((parent/name).read_bytes())
    (p/'action_envelope.py').write_bytes((HERE/'action_envelope.py').read_bytes())
    (p/'continuation_guard.py').write_bytes((HERE/'repair_runtime_guard.py').read_bytes())
    (p/'parent-full-plan.json').write_bytes((parent/'plan.json').read_bytes())
    (p/'private.token').write_bytes(secrets.token_hex(32).encode('ascii'))
    cut={'compatibility_version':VERSION,'frozen_total':len(full['queue']),'prefix_count':n,
         'first_new_run_id':full['queue'][n]['run_id'],'old_terminal_reruns':0,'resolver_only':True,
         'parent_runtime':{h:m['package'+h]for h in ('3090','4090')},'parent_model_output':m['output3090'],
         'parent_manifest_sha256':original['manifest_sha256'],'parent_plan_sha256':original['plan_sha256'],
         'gate_scorer_prompt_native_action_source_unchanged':True,
         'offline_qualification_sha256':sha(REPAIR/'offline-qualification.json')}
    save(p/'action-envelope-cutover.json',cut)
    edit(p/'paired_contract.py', [
        ("    assert m['trajectories'] == SAMPLE_COUNT * len(CONDITIONS) * 2 == len(plan['queue'])",
         "    assert m['action_envelope_compatibility'] == plan['action_envelope_compatibility']\n    assert m['trajectories'] == len(plan['queue'])"),
        ("    assert plan['queue'] == queue_for([row['task_id'] for row in plan['tasks']])",
         "    parent_file = root / 'parent-full-plan.json'\n    parent = json.loads(parent_file.read_bytes())\n    cut = json.loads((root/'action-envelope-cutover.json').read_bytes())\n    assert cut['parent_plan_sha256'] == hashlib.sha256(parent_file.read_bytes()).hexdigest()\n    split = cut['prefix_count']\n    assert type(split) is int and 0 < split < SAMPLE_COUNT * len(CONDITIONS) * 2 and split % 2 == 0\n    assert parent['queue'] == queue_for([row['task_id'] for row in parent['tasks']])\n    assert plan['queue'] == parent['queue'][split:] and plan['tasks'] == parent['tasks']\n    assert {k:v for k,v in plan.items() if k not in ('queue','action_envelope_compatibility')} == {k:v for k,v in parent.items() if k!='queue'}"),
    ])
    edit(p/'gui_experiment.py', [
        ('from paired_contract import load_plan,missing_image_request',
         'from paired_contract import load_plan,missing_image_request\nfrom action_envelope import parse_model_reply'),
        ("            p=self.native_parse(text)\n            if p['type']=='tab':assert 0<=int(p['index'])<len(self.env.context.pages),'Tab out of range'\n            else:self.action(p)\n            return p",
         "            p,envelope=parse_model_reply(text,self.native_parse)\n            if p['type']=='tab':assert 0<=int(p['index'])<len(self.env.context.pages),'Tab out of range'\n            else:self.action(p)\n            if envelope is not None:self.log.emit('native_action_envelope_normalized',{'step':self.step,**envelope})\n            return p"),
    ])
    edit(p/'launch_group.py', [(Path(m['package3090']).name + '.lock', case + '.lock')])
    plan={**full,'queue':full['queue'][n:],'action_envelope_compatibility':VERSION}
    plan_out=p/'plan.json'
    with plan_out.open('w',encoding='utf8',newline='\n')as f:json.dump(plan,f,ensure_ascii=False,indent=2)
    names=['continuation_guard.py','paired_contract.py','gui_experiment.py','launch_group.py','plan.json']
    assert all(sha(p/k)==h for k,h in m['files'].items() if k not in names)
    for name in ('capture_source.py','capture_client.py','injection.py','flash/gate_core.py','primary_server.py',
                 'actor-template.json','native-parser-source.py','gui_outer.py','explicit-placement.json','native_environment.py'):
        assert sha(parent/name)==sha(p/name),name
    files = {q.relative_to(p).as_posix(): sha(q) for q in sorted(p.rglob('*')) if q.is_file() and q.name not in ('manifest.json','private.token')}
    for name in files:
        if name.endswith('.py'):ast.parse((p/name).read_bytes(),filename=name)
    manifest={**m,'files':files,'trajectories':len(plan['queue']),'plan_sha256':sha(plan_out),
              'action_envelope_compatibility':VERSION,'auth_token_sha256':sha(p/'private.token'),
              'package3090':f'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/{case}',
              'package4090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/runtime',
              'output3090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/model-attempt-01'}
    save(p/'manifest.json',manifest)
    pointer={'root':str(root),'runtime':str(p),'manifest_sha256':sha(p/'manifest.json'),'plan_sha256':sha(plan_out),
             'planned_suffix':len(plan['queue']),'old_prefix_if_drained_as_armed':n,'first_new_run_id':plan['queue'][0]['run_id']}
    save(ptr,pointer)
    print(json.dumps(pointer))


def setup():
    control.POINTER=read(REPAIR/'linked-current.json')
    control.ROOT=Path(control.POINTER['root']);control.PACKAGE=Path(control.POINTER['runtime'])
    assert sha(control.PACKAGE/'manifest.json')==control.POINTER['manifest_sha256']
    control.MANIFEST=read(control.PACKAGE/'manifest.json')
    assert all(sha(control.PACKAGE/k)==h for k,h in control.MANIFEST['files'].items())


def qualify_runtime():
    root=control.ROOT
    target=root/'cpu-native-qualification.json'
    assert not target.exists() and all((root/f'stage-{host}.json').exists() for host in ('3090','4090'))
    offline=read(REPAIR/'offline-qualification.json')
    exact=read(REPAIR/'actual-early-failures.json')['model']['result']['exact_distinct_replies_by_sha256']
    prior=Path(read(HERE/'frozen-current.json')['root'])/'cpu-native-qualification.json'
    assert read(prior)['result']['passed'] and read(prior)['result']['new_model_calls']==0
    binding=control.remote('4090',control.prefix('4090')+f'ACTUAL={exact!r}\n'+r'''
import ast,hashlib,json,os,sys
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)];from resource_guard import sha
from native_environment import NATIVE_ENV
os.environ.update(NATIVE_ENV)
runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01');sys.path[:0]=[str(runtime/'native'),str(runtime/'upstream')]
with redirect_stdout(sys.stderr):
 import run_reddit_internvl_smoke as n
assert sha(Path(n.__file__))==sha(p/'native-parser-source.py')
from gui_experiment import LiveAdapter
from paired_contract import load_plan
m,plan=load_plan(p);assert sha(p/'manifest.json')==EXPECTED
old=Path(json.loads((p/'action-envelope-cutover.json').read_bytes())['parent_runtime'][HOST])
def methods(q):
 tree=ast.parse(q.read_bytes());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef)and x.name=='LiveAdapter')
 return {f.name:ast.dump(f,include_attributes=False)for f in cls.body if isinstance(f,ast.FunctionDef)}
old_methods=methods(old/'gui_experiment.py');new_methods=methods(p/'gui_experiment.py')
assert set(old_methods)==set(new_methods) and [k for k in old_methods if old_methods[k]!=new_methods[k]]==['parse']
def bind(text):
 log=[];a=SimpleNamespace(native_parse=n.parse,action=n.action,env=SimpleNamespace(context=SimpleNamespace(pages=[None])),
  step=1,log=SimpleNamespace(emit=lambda k,d:log.append((k,d))))
 payload=LiveAdapter.parse(a,text);return payload,log
checked=[]
for h,v in ACTUAL.items():
 text=v['text'];assert hashlib.sha256(text.encode()).hexdigest()==h
 action,log=bind(text);assert action['type']=='click' and len(log)==1 and log[0][1]['original_reply_sha256']==h
 expected={146:(403,567),155:(605,419)}[v['task_id']]
 assert (action['x'],action['y'])==expected
 native=n.action(action);coords=native['coords'].tolist()
 assert all(abs(value-ref/1000)<1e-7 for value,ref in zip(coords,expected))
 checked.append({'task':v['task_id'],'actual_reply_sha256':h,'coordinates_unchanged':True,'native_executor_coordinates':coords})
assert bind('<action>{"type":"wait"}</action>')==({'type':'wait'},[])
print(json.dumps({'passed':True,'manifest_sha256':EXPECTED,'planned_remaining_pairs':len(plan['queue'])//2,
 'actual_native_parse_and_click_constructor':checked,'native_direct_wait_binding':True,'native_actor_executor_capture_gate_scores_unchanged':True,
 'new_model_calls':0,'new_GUI_actions':0,'new_scorer_calls':0,'GPU_used':False}))
''','qualify-linked-real-native-action-constructor',timeout=55)
    assert binding['result']['passed'] and offline['status']=='passed'
    save(target,{**binding,'offline_qualification_sha256':sha(REPAIR/'offline-qualification.json'),
                 'unchanged_original_CPU_forward_qualification_sha256':sha(prior)})
    return binding['result']


def qualify_saved(operation):
    """Only repair the wrapper receipt if an import banner preceded successful JSON."""
    operation = Path(operation).resolve()
    assert operation.parent == (control.ROOT/'operations').resolve()
    assert operation.name.endswith('-qualify-linked-real-native-action-constructor-4090')
    seal = read(operation/'seal.json')
    assert all(sha(operation/name)==h for name,h in seal.items())
    transport=read(operation/'transport.json')
    assert transport['host']=='4090' and transport['returncode']==0
    lines=(operation/'stdout.bin').read_text(encoding='utf8').splitlines()
    assert lines[:-1] == ['Google Cloud not set up, skipping import of vertexai.preview.generative_models.Image']
    result=json.loads(lines[-1]);assert result['passed'] and result['manifest_sha256']==control.POINTER['manifest_sha256']
    assert result['planned_remaining_pairs']==control.POINTER['planned_suffix']//2
    assert result['new_model_calls']==result['new_GUI_actions']==result['new_scorer_calls']==0
    assert len(result['actual_native_parse_and_click_constructor'])==2
    prior=Path(read(HERE/'frozen-current.json')['root'])/'cpu-native-qualification.json'
    assert read(prior)['result']['passed']
    save(control.ROOT/'cpu-native-qualification.json',{
        'operation':str(operation),'result':result,'operation_seal_sha256':sha(operation/'seal.json'),
        'preliminary_reporting_failure':'Native import banner preceded JSON; successful CPU subprocess unchanged.',
        'offline_qualification_sha256':sha(REPAIR/'offline-qualification.json'),
        'unchanged_original_CPU_forward_qualification_sha256':sha(prior)})
    return result


def release(host):
    return control.remote(host,control.prefix(host)+r'''
import json,sys
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from continuation_guard import release_status
from resource_guard import sha
assert sha(p/'manifest.json')==EXPECTED
print(json.dumps(release_status(p,HOST)))
''','check-exact-parent-pair-drain',timeout=45)


if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    else:
        setup()
        options={'stage':control.stage,'qualify':qualify_runtime,'qualify-saved':qualify_saved,'release':release,'inspect':control.inspect}
        print(json.dumps(options[sys.argv[1]](*sys.argv[2:])))
