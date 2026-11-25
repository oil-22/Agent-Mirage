"""Once-only new source-bound controller diagnostic; no GPU/GUI allocation."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'launch_focus_conflict_repair.py').read_text(encoding='utf-8')
changes={
"PREP=BASE/'focus-conflict-repair-development'":"PREP=BASE/'price-history-repair-development'",
"focus-conflict-repair-active-20261029.json":"price-history-repair-active-20261029.json",
"focus-conflict-repair-preflight-":"price-history-repair-preflight-",
"run_focus_conflict_repair.py":"run_price_history_repair.py",
"'max_calls':24":"'max_calls':28",
"'test_focus_history_conflict_scope']":"'test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_minimum_price_reason_scope','test_price_history_binding']",
}
for old,new in changes.items():
    assert old in s,old;s=s.replace(old,new)
exec(compile(s,str(BASE/'launch_price_history_repair.generated.py'),'exec'))
