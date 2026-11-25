from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'collect_focus_fullgui_terminal.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-history-fullgui-development'","PREP=BASE/'price-frame-fullgui-development'")
exec(compile(s,str(BASE/'collect_price_frame_fullgui_terminal.generated.py'),'exec'))
