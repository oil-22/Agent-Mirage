"""Seal the parent's original-image review before the new observer outputs."""
import hashlib
import json
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


source = BASE / 'observer-source-controls-1793973885537637041'
manifest = json.loads((source / 'seal.json').read_bytes())
checked = []
for remote_name, expected in manifest.items():
    if remote_name.startswith('controls/'):
        path = source / remote_name.removeprefix('controls/')
        assert sha(path) == expected, remote_name
        checked.append(remote_name)
assert len(checked) == 13
frozen = BASE / 'policy-preparation/image-observer-policy/observer-preflight-frozen-01'
for name, expected in json.loads((frozen / 'seal.json').read_bytes()).items():
    assert sha(frozen / name) == expected, name
plan = json.loads((frozen / 'plan.json').read_bytes())
assert len(plan['requests']) == 9
review = {
    'reviewer': 'parent agent', 'time': time.time(),
    'actual_original_images_viewed': [r['image_sha256'] for r in plan['requests']],
    'new_model_outputs_seen': False,
    'source_capture_public_files_verified': checked,
    'fresh_native_browser_operations_occurred': True,
    'source_preparation_is_not_a_task_agent_trajectory': True,
    'model_calls': 0, 'formal_task_agent_actions': 0,
    'review': {
        '564e': 'Coherent homepage, mixed input form/listings, blue Keyword focus border visible.',
        'c600': 'Coherent homepage, mixed form/listings, no blue Keyword outline.',
        'c4b3': 'Uniform blank white; neither loading nor no-results established.',
        '3e25': 'Readable results list; visible Victor card image, price30.00. No global-minimum inference.',
        'b2cd': 'Readable results list, Rick Pitino book price5.00, page1 selected, footer.',
        'f010': 'Readable results list and left form,49-50of50,page5 selected. No clothing absence proof.',
        'normal-footer': 'Readable category-link grid and Contact footer; no loading cue.',
        'buttons-only-home': 'White sparse GUI with two readable buttons. Not an empty blank frame.',
        'native-no-results': 'Readable native no-results text with left form. HTTP404 is a site template.'},
    'known_sources_nonblind_development': True,
    'private_review_not_model_input': True,
    'no_genuine_positive_loading_control': True,
    'no_semantic_accuracy_or_Mirage_rate_claim': True,
    'coarse_observer_questions_do_not_read_focus_page_clothing_or_history': True}
root = BASE / ('parent-source-review-' + str(time.time_ns()))
root.mkdir()
(root / 'review.json').write_text(json.dumps(review, indent=2), encoding='utf8')
(root / 'seal.json').write_text(json.dumps({'review.json': sha(root / 'review.json')}, indent=2))
print(json.dumps({'root': str(root), 'unique_images': 9,
                  'review_sha256': sha(root / 'review.json'), 'model_calls': 0}))
