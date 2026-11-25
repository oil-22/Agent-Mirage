from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'launch_price_history_fullgui.py').read_text(encoding='utf-8')
s=s.replace('price-history-fullgui-development','price-frame-fullgui-development')
s=s.replace('price-history-fullgui-active-20261029.json','price-frame-fullgui-active-20261029.json')
s=s.replace('price-history-joint-stale-fullgui-','price-frame-joint-stale-fullgui-')
exec(compile(s,str(BASE/'launch_price_frame_fullgui.generated.py'),'exec'))
