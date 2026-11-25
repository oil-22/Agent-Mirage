from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'collect_native_direction_service_receipts.py').read_text(encoding='utf-8')
s=s.replace("PREP=BASE/'native-direction-development'","PREP=BASE/'price-frame-repair-development'")
s=s.replace("summary['new_model_calls']<=24","summary['new_model_calls']<=20")
s=s.replace("if kind in {'actor_request','verifier_request'}:","if kind=='verifier_request':")
s=s.replace("if kind in {'candidate','verifier_raw'}:","if kind=='verifier_raw':")
needle="        events=[json.loads(s)for s in(root/'journal'/case['id']/'events.jsonl').read_text(encoding='utf-8').splitlines()]"
assert s.count(needle)==1
s=s.replace(needle,"""        if not (root/'journal'/case['id']/'events.jsonl').exists():
            assert case['mode']=='routing' and not case['calls']
            chains.append({'case':case['id'],'events':0,'head':'0'*64,'scope':'No journal created by zero-call routing; no inferred chain'})
            continue
"""+needle)
exec(compile(s,str(BASE/'collect_price_frame_repair_receipts.generated.py'),'exec'))
