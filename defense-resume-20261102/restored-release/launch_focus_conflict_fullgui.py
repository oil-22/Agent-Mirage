"""Once-only authorized linked GUI validation; preserve all older active receipts."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'launch_focus_history_fullgui.py').read_text(encoding='utf-8')
source=source.replace("source=source.replace(\"PREP=BASE/'scoped-observability-development'\", \"PREP=BASE/'focus-history-fullgui-development'\")", "source=source.replace(\"PREP=BASE/'scoped-observability-development'\", \"PREP=BASE/'focus-conflict-fullgui-development'\")")
source=source.replace('focus-history-fullgui-active-20261029.json','focus-conflict-fullgui-active-20261029.json')
source=source.replace("'focus-history-joint-stale-fullgui-'+", "'focus-conflict-joint-stale-fullgui-'+")
exec(compile(source,str(BASE/'launch_focus_conflict_fullgui.generated.py'),'exec'))
