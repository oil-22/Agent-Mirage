"""New linked launcher, preserving original inherited-lock admission."""
from pathlib import Path
from ops import HERE, BASE

parent=BASE/'repair-evidence-20261109-01'
text=(parent/'stage_controls.py').read_text(encoding='utf8')
start=text.index('    source=HERE/\'runtime-package\'')
end=text.index('\ndef stage():')
text=text[:start]+'''    source=HERE/'runtime-package';dest=HERE/'controls-package'
    assert not dest.exists();dest.mkdir()
    for name in ['release','control-inputs','grammar-vendor']:
        shutil.copytree(source/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['model_runtime.py','resource_gate.py','preflight_support.py','aux_identity_support.py','four_gpu_contract.py',
                 'primary-reference.json','auxiliary-identity-reference.json','controls-plan.json','bounded_schema.py','native_format_bridge.py']:
        shutil.copy2(source/name,dest/name)
    shutil.copy2(HERE/'controls_worker.py',dest/'controls_worker.py')
    launcher=(BASE/'full-gui-single-evidence-20261108-01/runtime-package/launch_gui_service_once.py').read_text(encoding='utf8')
    launcher=launcher.replace('full-gui-single-evidence-20261108-01','bounded-evidence-20261109-02').replace('launch_gui_service_once.py','launch_controls_once.py').replace('gpu_server.py','controls_worker.py').replace('GUI_is_external_and_bound_to_plan','no_GUI_in_control_batch')
    (dest/'launch_controls_once.py').write_text(launcher,encoding='utf8',newline='\\n')
    for p in dest.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    check=HERE/'CPU-native-tokenizer-linked04-result.json'
    assert json.loads(check.read_bytes())['result']['returncode']==0
    lease=BASE/'resource-attempt-20261106-01/lease.json';l=json.loads(lease.read_bytes())
    m={'schema':'new-bounded-source-evidence-controls-v1','authorized_finite_joint_development':True,
       'authorization':'User sustained goal: 做实验做到防御有效果为止; new structural-only auxiliary condition',
       'expected_holder':l['holder'],'lease_sha256':sha(lease),'output':ROOT,'no_old_terminal_resume':True,
       'condition_and_tradeoffs_sha256':sha(HERE/'condition-and-tradeoffs.json'),'source_bindings_sha256':sha(HERE/'source-bindings.json'),
       'source_first_PRIVATE_expectation_seal_sha256':sha(HERE/'PRIVATE-source-first-expectations-seal.json'),
       'PRIVATE_expectations_excluded_from_worker':True,'native_CPU_receipt_sha256':sha(check),
       'worker_source_sha256':sha(dest/'controls_worker.py'),
       'files':{p.relative_to(dest).as_posix():sha(p)for p in sorted(dest.rglob('*'))if p.is_file()}}
    save(dest/'manifest.json',m)
    save(HERE/'controls-freeze.json',{'manifest_sha256':sha(dest/'manifest.json'),'plan_sha256':sha(dest/'controls-plan.json'),
         'auxiliary_cap':6,'main_cap':0,'format_retries':0,'actor_GUI_scorer_paid':0,'formal_efficacy':False})
    print(json.dumps({'frozen':str(dest),'manifest_sha256':sha(dest/'manifest.json'),'model_calls':0}))

''' +text[end:]
text=text.replace("path=commands/'repair-evidence-20261109-01.json'", "path=commands/'bounded-evidence-20261109-02.json'")
text=text.replace("('.new-repair-'", "('.new-bounded-'")
with(HERE/'stage_controls.py').open('x',encoding='utf8',newline='\n')as f:f.write(text)
inspection=(parent/'inspect_controls.py').read_text(encoding='utf8')
with(HERE/'inspect_controls.py').open('x',encoding='utf8',newline='\n')as f:f.write(inspection)
print('New stage/inspect helpers created; zero model calls.')
