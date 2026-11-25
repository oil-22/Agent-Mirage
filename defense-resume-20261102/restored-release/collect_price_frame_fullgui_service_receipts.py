"""Full wire/IDs/EOS audit of the new complete GUI; actual calls/scoring only."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'collect_native_direction_service_receipts.py').read_text(encoding='utf-8')
changes={
"PREP=BASE/'native-direction-development'":"PREP=BASE/'price-frame-fullgui-development'",
"root=Path(pointer['collected_root']);summary=json.loads((root/'summary.json').read_bytes());template=json.loads((root/'release/native-vwa-request.json').read_bytes())": """root=Path(json.loads((PREP/'terminal-current.json').read_bytes())['directory']);attempt=next(root.glob('runs/*/attempt-*'))
    case=json.loads((attempt/'complete.json').read_bytes());case['id']='single-joint-stale'
    assert 0<case['actor_calls']<=70 and 0<case['verifier_calls']<=140
    summary={'results':[case],'new_model_calls':len(case['calls'])}
    release=Path(json.loads((PREP/'fullgui-staging-current.json').read_bytes())['release']);template=json.loads((release/'native-vwa-request.json').read_bytes())""",
"(root/'journal'/case['id']/'events.jsonl')":"(attempt/'events.jsonl')",
"summary['new_model_calls']<=24":"summary['new_model_calls']<=210",
"'gui_actions':0,'official_scores':0":"'gui_actions':case['environment_actions'],'official_scores':int(case['scoring_status']=='complete'),'scoring_status':case['scoring_status'],'official_reward':case['official_reward']",
}
for old,new in changes.items():assert s.count(old)==1,old;s=s.replace(old,new)
exec(compile(s,str(BASE/'collect_price_frame_fullgui_service_receipts.generated.py'),'exec'))
