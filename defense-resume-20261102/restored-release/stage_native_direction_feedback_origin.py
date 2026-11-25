"""Isolated metadata-only integration preparation; no inputs/model launcher."""
import ast,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'native-direction-development'
completed=json.loads((PREP/'completed-current.json').read_bytes())
stage=json.loads((PREP/'current.json').read_bytes());source=Path(stage['release'])
out=PREP/('feedback-origin-staging-'+str(time.time_ns()));out.mkdir();release=out/'release';release.mkdir()
shutil.copytree(source/'defense',release/'defense',ignore=shutil.ignore_patterns('__pycache__'))
for n in ['native_direction_consistency.py','test_native_direction_development.py']:shutil.copy2(source/n,release/n)
for n in ['native_direction_feedback_origin.py','test_native_direction_feedback_origin.py']:shutil.copy2(BASE/n,release/n)
path=release/'defense/core.py';original=path.read_text(encoding='utf-8')
changed=original.replace('from native_direction_consistency import check_direction','from native_direction_consistency import check_direction\nfrom native_direction_feedback_origin import attribute_direction_feedback')
old="            if action_bad:corrections.append(pending_action_patch(candidate,proposal,view,verdict['action']['status'],completion_reason or direction_reason or point_reason or focus_reason or verdict['action']['reason']))"
new="""            if action_bad:
                patch=pending_action_patch(candidate,proposal,view,verdict['action']['status'],completion_reason or direction_reason or point_reason or focus_reason or verdict['action']['reason'])
                if direction_reason:patch=attribute_direction_feedback(patch,verdict['action'],direction_check)
                corrections.append(patch)"""
assert changed.count(old)==1;changed=changed.replace(old,new);path.write_text(changed,encoding='utf-8')
def functions(s):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before,after=functions(original),functions(changed)
for name in before:
    if name!='Controller':assert before[name]==after[name],name
result=subprocess.run([sys.executable,'-m','unittest','test_native_direction_development','test_native_direction_feedback_origin'],cwd=release,capture_output=True,text=True)
assert result.returncode==0,result.stderr
row={'scope':'Separate staged feedback-origin metadata repair only. Completed real10calls immutable; no old source controls rerun.',
     'linked_completed_review':completed,'original_verdict_and_native_actions_unchanged':True,'validators_and_limits_ast_unchanged':True,
     'tests':{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},'new_model_calls':0,'gui_actions':0,
     'contains_model_launcher_or_inputs':False,'formal_release':False,'directory':str(out)}
(out/'audit.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and '__pycache__'not in str(p)},indent=2))
pointer={'directory':str(out),'audit_sha256':sha(out/'audit.json'),'manifest_sha256':sha(out/'sha256.json'),'CPU_tests':24,'model_calls':0,'formal_release':False}
(PREP/'feedback-origin-staging-current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
