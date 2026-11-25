"""New fullGUI staging from the already measured v4.0.2 repair; no inference."""
from pathlib import Path

BASE = Path(__file__).resolve().parent
source = (BASE / 'stage_scoped_fullgui_preflight.py').read_text(encoding='utf-8')
source = source.replace("PREP=BASE/'scoped-observability-development'", "PREP=BASE/'focus-history-fullgui-development';PREP.mkdir(exist_ok=True)")
start = source.index("parent=json.loads((PREP/'live-candidate-current.json')")
end = source.index("(release/'tests').mkdir()", start)
source = source[:start] + '''parent=json.loads((BASE/'focus-history-repair-development/readiness-supplement/current.json').read_bytes());old=Path(parent['directory'])
for n,h in json.loads((old/'source-sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
out=PREP/('fullgui-stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
assert "DEFENSE_VERSION='evidence-v4.0.2-dev-current-only-scope-20261028'" in (release/'defense/core.py').read_text(encoding='utf-8')
''' + source[end:]
source = source.replace("(release/'tests').mkdir()", "(release/'tests').mkdir(exist_ok=True)")
source = source.replace("'test_scoped_controller_integration']", "'test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller']")
source = source.replace('scoped-fullgui-preparation-active-20261028.json', 'focus-history-fullgui-preparation-active-20261029.json')
source = source.replace("'scoped-fullgui-preparation-'+", "'focus-history-fullgui-preparation-'+")
source = source.replace("'formal_execution_authorized':False", "'formal_execution_authorized':True")
exec(compile(source, str(BASE / 'prepare_focus_history_fullgui.generated.py'), 'exec'))
