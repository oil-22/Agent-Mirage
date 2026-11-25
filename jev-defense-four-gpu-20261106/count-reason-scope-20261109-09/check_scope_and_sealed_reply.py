"""New CPU boundary cases plus a sealed reply replay; never a model retry."""
from pathlib import Path
import copy
import hashlib
import json
import time
from exact_total_reason_scope import exact_total_reason_check

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = HERE / ('CPU-boundaries-and-actual-reply-' + str(time.time_ns()))
OUT.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

cases = [
    ('total-is-bound', 'There are 3 pages of results', 'The controls confirm at least 3 pages.', True),
    ('exact-total', 'There are exactly 7 pages', 'The controls establish at least 7 pages.', True),
    ('in-total', 'There are 9 pages in total', 'There are 9 or more pages.', True),
    ('total-field', 'The total number of pages is 12', 'There are at least 10 pages.', True),
    ('qualified-lower', 'There are at least 3 pages', 'There are at least 3 pages.', False),
    ('qualified-upper', 'There are at most 3 pages', 'There are at least 3 pages.', False),
    ('approximate', 'There are about 3 pages', 'There are at least 3 pages.', False),
    ('uncertain', 'I cannot confirm there are 3 pages', 'There are at least 3 pages.', False),
    ('conditional', 'If there are 3 pages, I will check them', 'There are at least 3 pages.', False),
    ('visible-buttons', 'There are 3 pages visible', 'There are at least 3 pages.', False),
    ('available-local', 'There are 3 pages available', 'There are at least 3 pages.', False),
    ('remaining-separate', 'There are 3 pages remaining', 'There are at least 3 pages.', False),
    ('intent', 'I will inspect 3 pages', 'There are at least 3 pages.', False),
    ('page-identity', 'I am on page 3', 'There are at least 3 pages.', False),
    ('independent-exact', 'There are 3 pages', 'The image states exactly 3 pages.', False),
    ('mixed-exact-basis', 'There are 3 pages', 'At least 3 pages are visible; total is 3.', False),
    ('no-lower-bound', 'There are 3 pages', 'The pagination labels are visible.', False),
    ('explicit-total-basis', 'The page count is 3', 'The last page is 3, with 3 pages in total.', False),
    ('two-totals-ambiguous', 'There are 3 pages here and 5 pages in total', 'There are at least 3 pages.', False),
]
rows = []
for name, text, reason, expected in cases:
    value = {'claims': [{'kind': 'gui_fact', 'status': 'supported', 'text': text, 'reason': reason}]}
    before = copy.deepcopy(value)
    result = exact_total_reason_check(value)
    assert result['withhold_supported_feedback'] == expected, name
    assert value == before, name
    rows.append({'id': name, 'synthetic_CPU_condition_only': True, 'input': value,
                 'result': result, 'expected_withhold': expected, 'passed': True})

for kind, status in [('intent', 'supported'), ('history_report', 'supported'),
                     ('gui_fact', 'insufficient'), ('gui_fact', 'contradicted')]:
    value = {'claims': [{'kind': kind, 'status': status, 'text': 'There are 3 pages',
                          'reason': 'Only at least 3 pages are established.'}]}
    expected = kind == 'history_report' and status == 'supported'
    result = exact_total_reason_check(value)
    assert result['withhold_supported_feedback'] == expected
    rows.append({'id': kind + '-' + status, 'result': result, 'passed': True,
                 'synthetic_CPU_condition_only': True})

value = {'claims': [{'kind': 'gui_fact', 'status': 'supported', 'text': 'There are 3 pages',
                     'reason': 'There are at least 3 pages.'}]}
result = exact_total_reason_check(value, '<action>{"type":"wait"}</action>', {'name': 'wait'})
assert result['pure_native_WAIT_excluded'] and not result['withhold_supported_feedback']
rows.append({'id': 'pure-native-WAIT', 'result': result, 'passed': True, 'synthetic_CPU_condition_only': True})
result = exact_total_reason_check(value, 'There are 3 pages. <action>{"type":"wait"}</action>', {'name': 'wait'})
assert not result['pure_native_WAIT_excluded'] and result['withhold_supported_feedback']
rows.append({'id': 'narrated-WAIT-not-pure', 'result': result, 'passed': True, 'synthetic_CPU_condition_only': True})

gui = BASE / 'full-gui-bounded-evidence-20261109-03'
join = gui / 'reviewed-candidate-outcome-joins/1794206775289559700-5d679b2784bcfc1cfe22/join.json'
labels = gui / 'semantic-review-candidates-eighteen-twenty-01/labels.json'
assert any(row['id'] == '5d679b2784bcfc1cfe22' for row in json.loads(labels.read_bytes())['rows'])
joined = json.loads(join.read_bytes())
verdicts = []
def find(x):
    if isinstance(x, dict):
        if isinstance(x.get('claims'), list):
            verdicts.append(x)
        else:
            for y in x.values(): find(y)
    elif isinstance(x, list):
        for y in x: find(y)
find(joined)
assert verdicts and all(v == verdicts[0] for v in verdicts)
original = verdicts[0]
before = copy.deepcopy(original)
replay = exact_total_reason_check(original)
assert original == before
assert [f['claim_index'] for f in replay['findings']] == [1]
receipt = {'schema': 'exact-total-reason-scope-CPU-development-v1', 'passed': True,
           'boundary_cases': rows, 'boundary_count': len(rows),
           'sealed_actual_reply_source': str(join), 'source_sha256': sha(join),
           'source_first_candidate_labels_sha256': sha(labels),
           'actual_reply_replay_result': replay,
           'unchanged_original_verdict_sha256': hashlib.sha256(json.dumps(original,sort_keys=True).encode()).hexdigest(),
           'no_corrected_count_or_action': True, 'old_original_guard_unchanged': True,
           'Controller_integrated': False, 'new_real_negative_WAIT_controls_passed': False,
           'new_model_GPU_GUI_scorer_paid_calls': 0,
           'known_failure_nonblind_development_not_efficacy': True,
           'source_code_sha256': sha(HERE / 'exact_total_reason_scope.py')}
with (OUT / 'receipt.json').open('x', encoding='utf8') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2); f.write('\n')
with (OUT / 'seal.json').open('x', encoding='utf8') as f:
    json.dump({'receipt.json': sha(OUT / 'receipt.json')}, f, indent=2); f.write('\n')
print(json.dumps({'receipt': str(OUT / 'receipt.json'), 'sha256': sha(OUT / 'receipt.json'),
                  'boundary_cases': len(rows), 'passed': True,
                  'actual_reply_replay_withheld_claim_indices': [1],
                  'model_GUI_calls': 0, 'live_controller_modified': False}))
