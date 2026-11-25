"""Prepare one independent GUI attempt from an audited single-frame diagnostic."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'prepare_price_history_fullgui.py').read_text(encoding='utf-8')
s=s.replace('price-history-fullgui-development','price-frame-fullgui-development').replace('price-history-repair-development','price-frame-repair-development')
s=s.replace('evidence-v4.0.4-dev-price-history-binding-20261029','evidence-v4.0.4a-dev-single-frame-price-clause-20261029')
s=s.replace('price-history-fullgui-preparation','price-frame-fullgui-preparation')
s=s.replace("'test_price_history_controller']", "'test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller']")
exec(compile(s,str(BASE/'prepare_price_frame_fullgui.generated.py'),'exec'))
