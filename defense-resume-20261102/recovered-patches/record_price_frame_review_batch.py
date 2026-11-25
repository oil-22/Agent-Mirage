from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'record_focus_conflict_review_batch.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-conflict-fullgui-development'","PREP=BASE/'price-frame-fullgui-development'")
exec(compile(s,str(BASE/'record_price_frame_review_batch.generated.py'),'exec'))
