"""Prepare fresh linked source copies. Does not deploy or launch anything."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
release=HERE/'release';original=ROOT/'gui-preparation-package-02/release'
assert not(release/'observer_launch_contract.py').exists(),'Prepare once; preserve any failed source'
shutil.copytree(original,release,dirs_exist_ok=True)
shutil.copy2(ROOT/'gui-preparation-package-02/plan.json',release/'frozen-original-plan.json')
shutil.copy2(ROOT/'policy-preparation/image-observer-policy/gui-migration-three-01/cpu-preparation/1793984609630698800/plan.proposed.json',HERE/'plan.json')
gate=release/'observer_launch_contract.py';text=gate.read_text(encoding='utf8')
text=text.replace('from image_observer import POLICY,MODEL,REVISION,wire,contract,SHARED_ACTOR_INSTRUCTIONS',
    'from image_observer import POLICY,MODEL,REVISION,wire,contract,SHARED_ACTOR_INSTRUCTIONS\nfrom migration_contract import validate_three_plan,validate_migration_source')
start=text.index("    q=p['queue']\n");end=text.index("    if p['shared_actor_instructions_sha256']",start)
text=text[:start]+"    validate_three_plan(p)\n    validate_migration_source(evidence(r,'three_trajectory_migration'))\n"+text[end:]
text=text.replace("'terminal_auditor':['ready'", "'resource_conditions':['decoder_layers14_22_22_6','allocator_expandable_segments','new_capacity_not_old15720','all_three_same_resource'],\n      'terminal_auditor':['ready'")
text=text.replace("'defense/core.py','defense/prompts.py']", "'defense/core.py','defense/prompts.py','migration_contract.py','frozen-original-plan.json']")
gate.write_text(text,encoding='utf8')
runner=release/'run_image_observer_vwa_validation.py';text=runner.read_text(encoding='utf8')
before="queue=[q for q in plan['queue']if q['dataset']=='vwa'];assert len(queue)==4 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue) and {(q['observer_enabled'],q['condition'])for q in queue}=={(False,'clean'),(True,'clean'),(False,'stale_replace'),(True,'stale_replace')}"
after="from migration_contract import validate_three_plan\n queue=validate_three_plan(plan)"
assert text.count(before)==1;text=text.replace(before,after);runner.write_text(text,encoding='utf8')
auditor=HERE/'terminal-auditor';shutil.copytree(ROOT/'policy-preparation/image-observer-policy/terminal-auditor-linked-02',auditor,
    ignore=shutil.ignore_patterns('__pycache__','cpu-evidence'))
p=auditor/'audit_gui_terminals.py';text=p.read_text(encoding='utf8')
text=text.replace("sys.path.insert(0,str(Path(__file__).resolve().parents[1]))", "sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'release'))")
text=text.replace('from image_observer import (POLICY,MODEL,REVISION,STATE,QUESTIONS,contract,wire,',
    'from migration_contract import validate_three_plan,validate_migration_source\nfrom image_observer import (POLICY,MODEL,REVISION,STATE,QUESTIONS,contract,wire,')
text=text.replace("require(plan['policy']==POLICY and len(plan['queue'])==4,'Unbound GUI plan')",
    "require(plan['policy']==POLICY,'Unbound GUI policy');validate_three_plan(plan)\n    migration=spec['three_trajectory_migration'];require(sha(Path(migration['path']).read_bytes())==migration['sha256'],'Migration proof SHA differs')\n    validate_migration_source(read(migration['path']))")
text=text.replace('all_four_trajectories_complete','all_three_trajectories_complete').replace("len(rows)==4 and all(r['complete']for r in rows)","len(rows)==3 and all(r['complete']for r in rows)")
p.write_text(text,encoding='utf8')
wrapper=ROOT/'policy-preparation/image-observer-policy/gui-once-wrapper-retry01'
shutil.copy2(wrapper/'native_environment.py',HERE/'native_environment.py')
shutil.copy2(wrapper/'validate_native_environment.py',HERE/'validate_native_environment.py')
unchanged=['image_observer.py','online_transport.py','defense/core.py','defense/prompts.py','current_only_history_scope.py']
for name in unchanged:assert hashlib.sha256((original/name).read_bytes()).digest()==hashlib.sha256((release/name).read_bytes()).digest()
for p in HERE.rglob('*.py'):compile(p.read_text(encoding='utf8'),str(p),'exec')
diff={'stage':'linked_sources_only_not_deployed','plan_sha256':hashlib.sha256((HERE/'plan.json').read_bytes()).hexdigest(),
    'changed_release_files':['observer_launch_contract.py','run_image_observer_vwa_validation.py'],
    'new_release_files':['migration_contract.py','frozen-original-plan.json'],
    'original_algorithm_prompts_unchanged':unchanged,'resource_semantics':'decoder layer counts14/22/22/6; max_memory_gib separate',
    'new_online_service_source_owner':'prepare_four_gpu_worker','launch_ready':False,'model_GUI_calls':0}
(HERE/'source-preparation.json').write_text(json.dumps(diff,indent=2),encoding='utf8')
print(json.dumps(diff))
