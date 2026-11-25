"""Prepare a NEW GUI namespace with unchanged native condition and zero-model live check."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'stage_scoped_fullgui_preflight.py').read_text(encoding='utf-8')
s=s.replace("PREP=BASE/'scoped-observability-development'", "PREP=BASE/'price-history-fullgui-development';PREP.mkdir(exist_ok=True)")
start=s.index("parent=json.loads((PREP/'live-candidate-current.json')")
end=s.index("(release/'tests').mkdir()",start)
s=s[:start]+'''parent=json.loads((BASE/'price-history-repair-development/completed-current.json').read_bytes())
assert parent['worker_exited'] and parent['source_review_complete'] and parent['fullgui_candidate_eligible']
old=Path(json.loads((BASE/'price-history-repair-development/current.json').read_bytes())['directory'])
for n,h in json.loads((old/'source-sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
out=PREP/('fullgui-stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(BASE/'test_price_history_controller.py',release/'test_price_history_controller.py')
assert "evidence-v4.0.4-dev-price-history-binding-20261029" in (release/'defense/core.py').read_text(encoding='utf-8')
''' +s[end:]
s=s.replace("(release/'tests').mkdir()","(release/'tests').mkdir(exist_ok=True)")
s=s.replace("'test_scoped_controller_integration']", "'test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller']")
s=s.replace('scoped-fullgui-preparation-active-20261028.json','price-history-fullgui-preparation-active-20261029.json')
s=s.replace("'scoped-fullgui-preparation-'+", "'price-history-fullgui-preparation-'+")
s=s.replace("'formal_execution_authorized':False","'formal_execution_authorized':True")
old="held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()]\n assert len(held)>=len(locks)"
new="""held=[]
 for f in (proc/'fdinfo').iterdir():
  try:
   info=f.read_text()
   if 'FLOCK' in info:held.append({'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':info})
  except FileNotFoundError:pass
 assert all(any(x['target']==f.name for x in held)for f in locks),held"""
assert s.count(old)==1;s=s.replace(old,new)
exec(compile(s,str(BASE/'prepare_price_history_fullgui.generated.py'),'exec'))
