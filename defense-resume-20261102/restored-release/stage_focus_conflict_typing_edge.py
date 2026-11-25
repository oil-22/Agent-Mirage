"""Preserve the launched release, reproduce a control-flow defect in a linked copy."""
import ast,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-typing-edge-development';PREP.mkdir(exist_ok=True)
assert not(PREP/'current.json').exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
parent=json.loads((BASE/'focus-conflict-repair-development/current.json').read_bytes());old=Path(parent['directory'])
assert sha((old/'source-sha256.json').read_bytes())==parent['source_manifest_sha256']
for n,h in json.loads((old/'source-sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
out=PREP/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(BASE/'test_focus_conflict_typing_flow.py',release/'test_focus_conflict_typing_flow.py')
def test():
    p=subprocess.run([sys.executable,'-m','unittest','test_focus_conflict_typing_flow'],cwd=release,capture_output=True,text=True)
    return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
before=test();(out/'before-repair.json').write_text(json.dumps(before,indent=2));assert before['returncode']!=0 and 'FAIL:'in before['stderr']
p=release/'defense/core.py';s=p.read_text(encoding='utf-8');needle="focus_reason=crosscheck['reason'];point_needs_evidence="
assert s.count(needle)==1
s=s.replace(needle,"focus_reason=focus_reason or crosscheck['reason'];point_needs_evidence=")
s=s.replace('evidence-v4.0.3-dev-focus-conflict-plan-source-20261029','evidence-v4.0.3a-dev-focus-conflict-preserved-20261029')
p.write_text(s,encoding='utf-8')
defs=lambda x:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(x).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=defs((old/'release/defense/core.py').read_text(encoding='utf-8'));b=defs(s);assert set(a)==set(b)and[k for k in a if a[k]!=b[k]]==['Controller']
after=test();(out/'after-repair.json').write_text(json.dumps(after,indent=2));assert after['returncode']==0
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(release),'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'parent_manifest_sha256':parent['source_manifest_sha256'],'baseline_regression_failed':True,'repaired_tests':2,'new_inference':0,'formal_release':False}
(PREP/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
