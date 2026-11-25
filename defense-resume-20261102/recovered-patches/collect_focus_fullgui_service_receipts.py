"""Apply the existing full wire/ID/EOS auditor to this completed single GUI trajectory."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'collect_native_direction_service_receipts.py').read_text(encoding='utf-8')
s=s.replace("PREP=BASE/'native-direction-development'","PREP=BASE/'focus-history-fullgui-development'")
old="root=Path(pointer['collected_root']);summary=json.loads((root/'summary.json').read_bytes());template=json.loads((root/'release/native-vwa-request.json').read_bytes())"
new="""root=Path(json.loads((PREP/'terminal-current.json').read_bytes())['directory']);attempt=next(root.glob('runs/*/attempt-*'))
    case=json.loads((attempt/'complete.json').read_bytes());case['id']='single-joint-stale';summary={'results':[case],'new_model_calls':len(case['calls'])}
    assert case['actor_calls']==22<=70 and case['verifier_calls']==66<=140
    release=Path(json.loads((PREP/'fullgui-staging-current.json').read_bytes())['release']);template=json.loads((release/'native-vwa-request.json').read_bytes())"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("(root/'journal'/case['id']/'events.jsonl')","(attempt/'events.jsonl')")
s=s.replace("summary['new_model_calls']<=24","summary['new_model_calls']==88<=210")
s=s.replace("'gui_actions':0,'official_scores':0", "'gui_actions':case['environment_actions'],'official_scores':1")
exec(compile(s,str(BASE/'collect_focus_fullgui_service_receipts.generated.py'),'exec'))
