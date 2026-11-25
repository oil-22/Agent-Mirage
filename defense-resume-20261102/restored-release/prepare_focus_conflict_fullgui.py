"""New linked fullGUI candidate; retain failed diagnostics and original budgets."""
from pathlib import Path

BASE=Path(__file__).resolve().parent
source=(BASE/'stage_scoped_fullgui_preflight.py').read_text(encoding='utf-8')
source=source.replace("PREP=BASE/'scoped-observability-development'", "PREP=BASE/'focus-conflict-fullgui-development';PREP.mkdir(exist_ok=True)")
start=source.index("parent=json.loads((PREP/'live-candidate-current.json')")
end=source.index("(release/'tests').mkdir()",start)
source=source[:start]+'''parent=json.loads((BASE/'plan-present-report-repair-development/current.json').read_bytes());old=Path(parent['directory'])
for n,h in json.loads((old/'source-sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
out=PREP/('fullgui-stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
assert "evidence-v4.0.3b-dev-focus-plan-report-20261029"in(release/'defense/core.py').read_text(encoding='utf-8')
''' +source[end:]
source=source.replace("(release/'tests').mkdir()","(release/'tests').mkdir(exist_ok=True)")
source=source.replace("'test_scoped_controller_integration']", "'test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source']")
source=source.replace('scoped-fullgui-preparation-active-20261028.json','focus-conflict-fullgui-preparation-active-20261029.json')
source=source.replace("'scoped-fullgui-preparation-'+", "'focus-conflict-fullgui-preparation-'+")
source=source.replace("'formal_execution_authorized':False","'formal_execution_authorized':True")
old="held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()]\n assert len(held)>=len(locks)"
new="""held=[]
 for f in (proc/'fdinfo').iterdir():
  try:
   info=f.read_text()
   if 'FLOCK' in info:held.append({'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':info})
  except FileNotFoundError:pass
 assert all(any(x['target']==f.name for x in held)for f in locks),held"""
assert source.count(old)==1;source=source.replace(old,new)
exec(compile(source,str(BASE/'prepare_focus_conflict_fullgui.generated.py'),'exec'))
