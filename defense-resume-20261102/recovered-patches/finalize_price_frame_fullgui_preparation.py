from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'finalize_price_history_fullgui_preparation.py').read_text(encoding='utf-8')
s=s.replace('price-history-fullgui-development','price-frame-fullgui-development').replace('price-history-repair-development','price-frame-repair-development')
s=s.replace('evidence-v4.0.4-dev-price-history-binding-20261029','evidence-v4.0.4a-dev-single-frame-price-clause-20261029')
s=s.replace('launch_price_history_fullgui.py','launch_price_frame_fullgui.py').replace('price-history-fullgui-active-20261029.json','price-frame-fullgui-active-20261029.json')
s=s.replace('[122,132]','[122,140]').replace('254','262')
s=s.replace('read every original delivered frame for separate item-price rows without candidate or narrative, freeze SHA, compare factual price-object assertions in isolated text relation; never certify appearance or minimum from that relation', 'read each original delivered frame in a separate candidate/history-blind call, freeze its item-price facts by source SHA, reuse prior frozen reads as past data, and compare exact original historical-price clauses in an isolated text relation; never certify appearance or minimum from that relation')
exec(compile(s,str(BASE/'finalize_price_frame_fullgui_preparation.generated.py'),'exec'))
