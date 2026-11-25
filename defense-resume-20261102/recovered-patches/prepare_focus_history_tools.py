"""Make once-only tools for this separate repair, retaining old tools and terminals."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=BASE/'launch_focus_history_repair.py';assert not p.exists()
s=(BASE/'launch_scoped_observability.py').read_text(encoding='utf-8')
s=s.replace("'scoped-observability-development'","'focus-history-repair-development'")
s=s.replace("b/'scoped-observability-development.lock'","b/'focus-history-repair-development.lock'")
s=s.replace("b/'scoped-observability-development-active-20261028.json'","b/'focus-history-repair-active-20261028.json'")
s=s.replace("r=b/('scoped-observability-real-preflight-'","assert not(b/'scoped-fullgui-active-20261028.json').exists(),'Repair first, no fullGUI approval'\nr=b/('focus-history-repair-real-preflight-'")
start=s.index("tests=subprocess.run(");end=s.index("env=dict(",start)
s=s[:start]+'''results=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope']]:
 tests=subprocess.run([py]+args,cwd=r/'release',capture_output=True,text=True,timeout=60)
 results.append({'args':args,'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr})
(r/'remote-cpu-tests.json').write_text(json.dumps(results,indent=2));assert all(x['returncode']==0 for x in results),'Remote CPU failure preserved'
''' +s[end:]
s=s.replace('release/run_scoped_observability.py','release/run_focus_history_repair.py')
p.write_text(s,encoding='utf-8')
p=BASE/'inspect_focus_history_repair.py';assert not p.exists()
s=(BASE/'inspect_scoped_observability.py').read_text(encoding='utf-8').replace("'scoped-observability-development'","'focus-history-repair-development'").replace("'/scoped-observability-development.lock'","'/focus-history-repair-development.lock'")
p.write_text(s,encoding='utf-8')
p=BASE/'collect_focus_history_receipts.py';assert not p.exists()
s=(BASE/'collect_scoped_observability_receipts.py').read_text(encoding='utf-8').replace("'scoped-observability-development'","'focus-history-repair-development'")
p.write_text(s,encoding='utf-8')
print('Prepared separate once-only repair launcher, inspector and actual-service receipt collector')
