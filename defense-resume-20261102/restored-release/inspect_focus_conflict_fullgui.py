"""Actual UID/full command/held locks/event chains for this new single run."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'inspect_focus_history_fullgui.py').read_text(encoding='utf-8')
assert source.count("PREP=BASE/'focus-history-fullgui-development'")==1
source=source.replace("PREP=BASE/'focus-history-fullgui-development'","PREP=BASE/'focus-conflict-fullgui-development'")
exec(compile(source,str(BASE/'inspect_focus_conflict_fullgui.generated.py'),'exec'))
