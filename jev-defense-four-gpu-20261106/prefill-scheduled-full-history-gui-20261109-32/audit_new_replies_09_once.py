"""Audit only sealed requests0019..0020; preserve earlier completed audits."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'audit_new_replies_02_once.py').read_text(encoding='utf8')
changes = [
    ('new-replies-02-audit-created.json', 'new-replies-09-audit-created.json', 2),
    ('actual-evidence-1794230765210589400', 'actual-evidence-1794233539463615400', 1),
    ("record['sealed_requests'][1:4]", "record['sealed_requests'][18:20]", 1),
    ("len(rows)==3 and [row['request'] for row in rows] == ['0002','0003','0004']", "len(rows)==2 and [row['request'] for row in rows] == ['0019','0020']", 1),
    ("counts={'actor':17,'judge':51}", "counts={'actor':22,'judge':63}", 1),
    ("['original_track_attempt_index']==52", "['original_track_attempt_index']==64", 1),
    ('prefills[1:4]', 'prefills[18:20]', 1),
    ('linked32-only-new-replies2to4-native-tensor-prefill-audit-v1', 'linked32-only-new-replies19to20-native-tensor-prefill-audit-v1', 1),
    ('audit-only-new32-replies2to4-no-repeat-original-prefix-once', 'audit-only-new32-replies19to20-no-repeat-original-prefix-once', 1),
    ("'new-replies-02-audit-'", "'new-replies-09-audit-'", 1),
]
for before, after, count in changes:
    assert source.count(before) == count, before
    source = source.replace(before, after)
before = "assert len(item['visited_groups'])==69 and set(item['visited_groups'])==set(item['same_native_execution_device_map'])"
assert source.count(before) == 1
source = source.replace(before, "expected=set(item['same_native_execution_device_map'])\n if row['complete_supplied_images']==0:expected.remove('model.visual')\n assert set(item['visited_groups'])==expected and len(item['visited_groups'])==len(expected)\n row['actual_native_prefill_group_count']=len(expected)\n row['native_visual_forward_observed']='model.visual'in item['visited_groups']")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
