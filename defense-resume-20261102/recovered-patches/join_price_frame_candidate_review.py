from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'join_focus_conflict_candidate_review.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-conflict-fullgui-development'","PREP=BASE/'price-frame-fullgui-development'")
exec(compile(s,str(BASE/'join_price_frame_candidate_review.generated.py'),'exec'))
