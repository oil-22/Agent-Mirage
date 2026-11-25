"""Post-exit immutable fullGUI seal and public artifact collection, no inference."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'collect_focus_fullgui_terminal.py').read_text(encoding='utf-8')
source=source.replace("PREP=BASE/'focus-history-fullgui-development'","PREP=BASE/'focus-conflict-fullgui-development'")
source=source.replace("assert state['phase']=='completed'", "assert state['phase']=='paused_at_decision_boundary';assert len(list(r.glob('runs/*/attempt-*/paused.json')))==1;assert not list(r.glob('runs/*/attempt-*/complete.json'))")
exec(compile(source,str(BASE/'collect_focus_conflict_fullgui_terminal.generated.py'),'exec'))
