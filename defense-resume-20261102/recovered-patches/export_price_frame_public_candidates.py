from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'export_focus_conflict_public_candidates.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-conflict-fullgui-development'","PREP=BASE/'price-frame-fullgui-development'")
exec(compile(s,str(BASE/'export_price_frame_public_candidates.generated.py'),'exec'))
