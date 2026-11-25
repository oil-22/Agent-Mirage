"""Same full wire/input IDs/EOS/image/reply audit, scoped to the new diagnostic."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'collect_focus_readiness_supplement_receipts.py').read_text(encoding='utf-8')
source=source.replace("BASE/'focus-history-repair-development'/'readiness-supplement'", "BASE/'focus-conflict-repair-development'")
exec(compile(source,str(BASE/'collect_focus_conflict_repair_receipts.generated.py'),'exec'))
