"""Read-only incremental audit for already sealed GUI32 requests0012..0013."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'audit_new_replies_02_once.py').read_text(encoding='utf8')
changes = [
    ('new-replies-02-audit-created.json', 'new-replies-06-audit-created.json', 2),
    ('actual-evidence-1794230765210589400', 'actual-evidence-1794232466532971600', 1),
    ("record['sealed_requests'][1:4]", "record['sealed_requests'][11:13]", 1),
    ("len(rows)==3 and [row['request'] for row in rows] == ['0002','0003','0004']", "len(rows)==2 and [row['request'] for row in rows] == ['0012','0013']", 1),
    ("counts={'actor':17,'judge':51}", "counts={'actor':20,'judge':58}", 1),
    ("['original_track_attempt_index']==52", "['original_track_attempt_index']==59", 1),
    ('prefills[1:4]', 'prefills[11:13]', 1),
    ('linked32-only-new-replies2to4-native-tensor-prefill-audit-v1', 'linked32-only-new-replies12to13-native-tensor-prefill-audit-v1', 1),
    ('audit-only-new32-replies2to4-no-repeat-original-prefix-once', 'audit-only-new32-replies12to13-no-repeat-original-prefix-once', 1),
    ("'new-replies-02-audit-'", "'new-replies-06-audit-'", 1),
]
for before, after, count in changes:
    assert source.count(before) == count, before
    source = source.replace(before, after)
before = "assert len(item['visited_groups'])==69 and set(item['visited_groups'])==set(item['same_native_execution_device_map'])"
assert source.count(before) == 1
source = source.replace(before, "expected=set(item['same_native_execution_device_map'])\n if row['complete_supplied_images']==0:expected.remove('model.visual')\n assert set(item['visited_groups'])==expected and len(item['visited_groups'])==len(expected)\n row['actual_native_prefill_group_count']=len(expected)\n row['native_visual_forward_observed']='model.visual'in item['visited_groups']")
before = "assert native['text']==response['text'if operation=='actor'else'verdict']"
assert source.count(before) == 1
source = source.replace(before, before + "\n if operation=='actor':\n  assert native['verifier_grammar']is None\n  assert payload['body']['chat_template_kwargs']['enable_thinking']is False\n  for field in ['force_words_ids','forced_decoder_ids','forced_bos_token_id','constraints','bad_words_ids','suppress_tokens','begin_suppress_tokens']:\n   assert cfg.get(field)in [None,[]],field")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
