"""Read-only incremental audit for already sealed GUI32 requests0005..0007."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'audit_new_replies_02_once.py').read_text(encoding='utf8')
changes = {
    'new-replies-02-audit-created.json': 'new-replies-03-audit-created.json',
    'actual-evidence-1794230765210589400': 'actual-evidence-1794231307194812000',
    "record['sealed_requests'][1:4]": "record['sealed_requests'][4:7]",
    "['0002','0003','0004']": "['0005','0006','0007']",
    "counts={'actor':17,'judge':51}": "counts={'actor':18,'judge':53}",
    "['original_track_attempt_index']==52": "['original_track_attempt_index']==54",
    'prefills[1:4]': 'prefills[4:7]',
    'linked32-only-new-replies2to4-native-tensor-prefill-audit-v1': 'linked32-only-new-replies5to7-native-tensor-prefill-audit-v1',
    'audit-only-new32-replies2to4-no-repeat-original-prefix-once': 'audit-only-new32-replies5to7-no-repeat-original-prefix-once',
    "'new-replies-02-audit-'": "'new-replies-03-audit-'",
}
for before, after in changes.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)

before = "assert len(item['visited_groups'])==69 and set(item['visited_groups'])==set(item['same_native_execution_device_map'])"
assert source.count(before) == 1
source = source.replace(before, "expected=set(item['same_native_execution_device_map'])\n if row['complete_supplied_images']==0:expected.remove('model.visual')\n assert set(item['visited_groups'])==expected and len(item['visited_groups'])==len(expected)\n row['actual_native_prefill_group_count']=len(expected)\n row['native_visual_forward_observed']='model.visual'in item['visited_groups']")

before = "assert native['text']==response['text'if operation=='actor'else'verdict']"
assert source.count(before) == 1
source = source.replace(before, before + "\n if operation=='actor':\n  assert native['verifier_grammar']is None\n  assert payload['body']['chat_template_kwargs']['enable_thinking']is False\n  for field in ['force_words_ids','forced_decoder_ids','forced_bos_token_id','constraints','bad_words_ids','suppress_tokens','begin_suppress_tokens']:\n   assert cfg.get(field)in [None,[]],field")

exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
