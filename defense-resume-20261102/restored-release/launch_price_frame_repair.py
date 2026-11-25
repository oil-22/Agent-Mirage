"""Launch new single-frame diagnostic only after the older development worker exits."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'launch_focus_conflict_repair.py').read_text(encoding='utf-8')
changes={"PREP=BASE/'focus-conflict-repair-development'":"PREP=BASE/'price-frame-repair-development'",
"focus-conflict-repair-active-20261029.json":"price-frame-repair-active-20261029.json",
"focus-conflict-repair-preflight-":"price-frame-repair-preflight-",
"run_focus_conflict_repair.py":"run_price_frame_repair.py",
"'max_calls':24":"'max_calls':20",
"'test_focus_history_conflict_scope']":"'test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller']"}
for old,new in changes.items():assert old in s,old;s=s.replace(old,new)
exec(compile(s,str(BASE/'launch_price_frame_repair.generated.py'),'exec'))
