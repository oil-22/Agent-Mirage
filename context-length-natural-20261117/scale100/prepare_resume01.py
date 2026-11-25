"""Prepare a continuation cohort without rerunning or hiding model-format failures."""
from pathlib import Path
import shutil,json,hashlib,tarfile
P=Path(__file__).resolve().parent
Q=P.parent/'scale100-resume01'
assert Q.parent.resolve()==P.parent.resolve()
assert not (Q/'gui-output').exists() and not (Q/'model-launch-receipt.json').exists()
Q.mkdir(exist_ok=True)
names=['config.json','model_service.py','run_scale100.py','actor-template.json','native_environment.py','native-parser-source.py','tasks.json','native-bindings-public.json','prospective-plan.json','reference-image-manifest.json','README.md','service.token','deploy_scale100.py','check_status.py','export_results.py','verify_clean_prefix.py']
for name in names:shutil.copy2(P/name,Q/name)
for name in ['reference-images','PRIVATE-evaluator-configs']:shutil.copytree(P/name,Q/name,dirs_exist_ok=True)
old='/data/researcher/context-length-natural-20261117/scale100'
new=old+'-resume01'
cfg=json.loads((Q/'config.json').read_text());cfg.update(attempt='natural-scale100-resume01',resumed_from=old,change='Catch malformed native-action arguments at the task boundary; no actor/input/generation changes')
(Q/'config.json').write_text(json.dumps(cfg,indent=2))
src=(Q/'run_scale100.py').read_text()
oldblock="""    if payload['type']=='tab':
        assert 0<=int(payload['index'])<len(env.context.pages)
        action=create_page_focus_action(int(payload['index']))
    else:action=native.action(payload)
"""
newblock="""    # Invalid model action arguments terminate this task, not the entire cohort.
    # Do not coerce coordinates or send an extra repair prompt to the actor.
    try:
        if payload['type']=='tab':
            assert 0<=int(payload['index'])<len(env.context.pages)
            action=create_page_focus_action(int(payload['index']))
        else:action=native.action(payload)
    except (TypeError,ValueError,AssertionError,KeyError) as error:
        raise ValueError('Invalid native action payload: '+str(error)) from error
"""
assert src.count(oldblock)==1;src=src.replace(oldblock,newblock)
src=src.replace("assert terminal['outcome'] in ['model_stop','step_cap']", "assert terminal['outcome'] in ['model_stop','step_cap','native_parse_failure','native_action_contract_failure']")
src=src.replace("phase='completed_100_natural'", "phase='completed_100_task_trajectories'")
compile(src,str(Q/'run_scale100.py'),'exec');(Q/'run_scale100.py').write_text(src)
d=(Q/'deploy_scale100.py').read_text().replace("ROOT="+repr(old),"ROOT="+repr(new));(Q/'deploy_scale100.py').write_text(d)
binding=json.loads((Q/'native-bindings-public.json').read_text())
for row in binding['tasks']:row['original_private_path']=row['original_private_path'].replace(old,new)
(Q/'native-bindings-public.json').write_text(json.dumps(binding,indent=2))
plan=json.loads((Q/'prospective-plan.json').read_text());plan.update(resumed_from=old,format_failures='Model parse/action-contract failures are retained as failed task trajectories, separately from natural-stop/step-cap trajectories and Mirage labels; no rerun for a better outcome')
(Q/'prospective-plan.json').write_text(json.dumps(plan,indent=2))
(Q/'README.md').write_text((P/'README.md').read_text(encoding='utf8')+'\n\n## 2026-11-18 恢复说明\n\n原批次在 T157 首步输出列表坐标时触发未捕获 TypeError。原始输出和批次退出记录保留；补记该任务的动作格式失败终止，不重新生成或修正动作，不伪造任务得分。已终止的任务按原结果复用，只运行余下20个任务。格式失败与正常停止/步数上限分开统计，均不自动作为 Agent-Mirage 事件。\n',encoding='utf8')
files=[Q/n for n in names]+list((Q/'reference-images').iterdir())+list((Q/'PRIVATE-evaluator-configs').iterdir())
manifest={str(f.relative_to(Q)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.name!='service.token'}
(Q/'deployment-manifest.json').write_text(json.dumps(manifest,indent=2));files.append(Q/'deployment-manifest.json')
with tarfile.open(Q/'runtime-package.tar.gz','w:gz') as t:
    for f in files:t.add(f,arcname=str(f.relative_to(Q)).replace('\\','/'),recursive=False)
print(json.dumps(dict(prepared=str(Q),manifest_files=len(manifest))))
