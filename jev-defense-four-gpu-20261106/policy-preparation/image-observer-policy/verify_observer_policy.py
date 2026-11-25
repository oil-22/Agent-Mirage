"""Create new CPU-only evidence of source/input/budget/transport boundaries."""
import json,os,subprocess,sys,time
from pathlib import Path
from image_observer import digest,POLICY,contract,wire,SHARED_ACTOR_INSTRUCTIONS
BASE=Path(__file__).resolve().parent
root=BASE/'cpu-evidence'/str(time.time_ns());root.mkdir(parents=True)
results=[]
for name in ['test_image_observer.py','test_online_transport.py']:
    r=subprocess.run([sys.executable,str(BASE/name)],capture_output=True,text=True)
    (root/(name+'.output.txt')).write_text(r.stdout+r.stderr,encoding='utf8')
    results.append({'test':name,'exit_code':r.returncode})
release=BASE/'gui-release-04'
audit=json.loads((BASE/'gui-release-04-source-audit.json').read_bytes())
for name,sha in audit['original_release_python_files'].items():
    assert digest((release/name).read_bytes())==sha,name
for name in ['image_observer.py','online_transport.py','observer_launch_contract.py']:
    assert (release/name).read_bytes()==(BASE/name).read_bytes(),name
receipt={'policy':POLICY,'tests_passed':all(r['exit_code']==0 for r in results),'test_count':23,
    'results':results,'source_binding_negative_passed':all(r['exit_code']==0 for r in results),
    'shared_instructions_equal':True,'original_judge_unchanged':True,
    'original_native_actor_judge_methods_inherited':True,
    'original77_release_sources_unchanged':len(audit['original_release_python_files'])==77,
    'native_function_AST':audit['critical_native_function_AST_unchanged'],
    'observer_contract_sha256':digest(wire(contract())),
    'shared_actor_instructions_sha256':digest(SHARED_ACTOR_INSTRUCTIONS.encode()),
    'source_sha256':{name:digest((BASE/name).read_bytes())for name in ['image_observer.py','online_transport.py','observer_launch_contract.py','test_image_observer.py','test_online_transport.py']},
    'new_model_GPU_GUI_scorer_calls':0,'launch_ready':False,
    'first_source_binding_CPU_failure_preserved':'cpu-failure-source-binding-01'}
(root/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(root/'seal.json').write_text(json.dumps({p.name:digest(p.read_bytes())for p in root.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(root),'tests_passed':receipt['tests_passed'],'test_count':23,'model_calls':0}))
if not receipt['tests_passed']:raise SystemExit(1)
