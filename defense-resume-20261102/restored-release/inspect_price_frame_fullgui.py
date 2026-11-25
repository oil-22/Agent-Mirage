from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'inspect_focus_history_fullgui.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-history-fullgui-development'","PREP=BASE/'price-frame-fullgui-development'")
exec(compile(s,str(BASE/'inspect_price_frame_fullgui.generated.py'),'exec'))
