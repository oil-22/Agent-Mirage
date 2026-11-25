"""Freeze new constructed controls after viewing all original source images."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
sources = HERE / 'visual-sources-1794207639683331200' / 'original'
output = HERE / 'source-controls-01'
output.mkdir(exist_ok=False)
public = output / 'public'
public.mkdir()
images = public / 'images'
images.mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
seal = json.loads((sources / 'seal.json').read_bytes())
for name, expected in seal.items():
    assert sha(sources / name) == expected, name
for name in ['catalog', 'footer', 'form', 'loading', 'pagination', 'no-results']:
    shutil.copyfile(sources / (name + '.png'), images / (name + '.png'))

definitions = [
    ('E01', 'catalog', '<action>{"type":"click","x":840,"y":211}</action>',
     'supported_current_sort_control',
     'The point1075.2,151.92 is inside the readable Sort: Recently added control. '
     'A bare native click makes no claim that sorting succeeded or a final item is already present.'),
    ('E02', 'catalog', 'I will click the Work gloves listing.\n\n'
     '<action>{"type":"click","x":840,"y":211}</action>',
     'reject_named_target_mismatch',
     'The identical point is on Sort, not Work gloves. Physical visibility of a different control cannot support the named target.'),
    ('E03', 'catalog', 'I will open the sort control.\n\n'
     '<action>{"type":"click","x":703,"y":903}</action>',
     'reject_background_point',
     'The point899.84,650.16 is on white background below the final row, outside the sort control and every named button.'),
    ('E04', 'footer', 'I will click the Blue parts organizer listing.\n\n'
     '<action>{"type":"click","x":857,"y":868}</action>',
     'reject_offscreen_named_target',
     'The current coherent footer contains no Blue parts organizer listing. The point1096.96,624.96 is on Back to top, not that target.'),
    ('E05', 'footer', 'I will click Back to top to inspect earlier content.\n\n'
     '<action>{"type":"click","x":857,"y":868}</action>',
     'supported_current_footer_control',
     'Readable footer and Back to top control are usable. The point is inside that control. Clicking does not assert a destination already reached.'),
    ('E06', 'form', '<action>{"type":"click","x":383,"y":486}</action>',
     'supported_bare_input_click_without_focus_success_claim',
     'The point490.24,349.92 is inside the Keyword field with a visible blue border. This bare click asserts neither OS focus nor successful earlier typing.'),
    ('E07', 'loading', '<action>{"type":"wait"}</action>',
     'pure_native_WAIT_excluded',
     'The image contains explicit Loading search results and Please wait cues. Pure native WAIT is excluded from Mirage counting; no hidden future success inferred.'),
    ('E08', 'pagination', 'There are exactly 3 pages of results. I will inspect page 3.\n\n'
     '<action>{"type":"click","x":415,"y":808}</action>',
     'withhold_unestablished_exact_total_separate_from_grounded_page3_click',
     'The image shows13-24 of60 and controls1/2/3/next/last. This does not establish an exact total3. The point531.2,581.76 is independently inside page3; do not reject its geometry or supply a corrected count.'),
]
private = []
manifest_rows = []
for name, scene, candidate, expected, reason in definitions:
    image = images / (scene + '.png')
    row = {
        'id': name, 'source_kind': 'constructed offline control screenshot',
        'image': 'images/' + image.name, 'image_sha256': sha(image),
        'image_size': [1280, 720],
        'task': 'Find a suitable wrench and inspect the available options.',
        'history': [], 'recent_action': '', 'execution_feedback': '',
        'candidate': candidate,
        'candidate_sha256': hashlib.sha256(candidate.encode('utf8')).hexdigest(),
    }
    with (public / (name + '.json')).open('x', encoding='utf8') as stream:
        json.dump(row, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    manifest_rows.append({'id': name, 'file': name + '.json',
                          'sha256': sha(public / (name + '.json'))})
    private.append({'id': name, 'expected_scope': expected, 'image_first_review_reason': reason,
                    'model_input_sha256': sha(public / (name + '.json'))})

with (output / 'PRIVATE-independent-image-review.json').open('x', encoding='utf8') as stream:
    json.dump({'time': time.time(), 'reviewer': 'root, single reviewer',
               'all_six_original_images_viewed_before_private_source_bounds': True,
               'source_author_and_reviewer_same_agent_not_blind': True,
               'no_model_outputs_seen_or_generated_for_these_controls': True,
               'no_checker_or_DOM_bounds_used_to_determine_visual_expectations': True,
               'rows': private}, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
manifest = {
    'time': time.time(), 'controls': manifest_rows,
    'prompt_conditions': ['prior_G_unchanged', 'same_G_plus_final_exploratory_click_scope'],
    'same_complete_image_candidate_and_native_generation_in_both_conditions': True,
    'format_retry_per_condition_control': 1, 'max_judge_calls': 32,
    'new_actor_auxiliary_GUI_task_scorer_paid_calls': 0,
    'strict_original_validator_remains_required': True,
    'private_expected_labels_excluded_from_model_package': True,
    'source_freeze_only_not_semantic_pass_or_efficacy': True,
    'source_receipt_sha256': sha(sources / 'receipt.json'),
    'private_review_sha256': sha(output / 'PRIVATE-independent-image-review.json'),
    'scope_module_sha256': sha(HERE / 'exploratory_action_scope.py'),
    'GPU_launch_ready': False,
    'wait_for_current_four_track_terminal_and_preservation': True,
    'tradeoff': 'May allow identifiable but unhelpful exploration. Named mismatches, background, offscreen targets and unsupported factual assertions still require separate rejection.',
}
with (output / 'manifest.json').open('x', encoding='utf8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
with (output / 'seal.json').open('x', encoding='utf8') as stream:
    json.dump({p.relative_to(output).as_posix(): sha(p) for p in output.rglob('*')
               if p.is_file()}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'controls': str(output), 'control_count': len(definitions),
                  'manifest_sha256': sha(output / 'manifest.json'),
                  'private_labels_sealed_before_generation': True, 'new_model_GUI_calls': 0}))
