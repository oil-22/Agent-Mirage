"""Record actual visual review and the already-sent development question."""
import json
import time
from pathlib import Path

from remote_util import HERE, save, sha


def main():
    study = HERE.parent / 'flash-buttons-policy-proposal-20261116-07'
    assert not (study / 'decision-request-current.json').exists()
    pointer = json.loads((study / 'proposal-current.json').read_bytes())
    prepared = Path(pointer['root'])
    assert sha(prepared / 'seal.json') == pointer['seal_sha256']
    for name, expected in json.loads((prepared / 'seal.json').read_bytes()).items():
        assert sha(prepared / name) == expected
    controls = json.loads((prepared / 'control-plan.json').read_bytes())
    images = {v['id']: v for v in controls['rows']}
    root = study / ('review-and-question-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'visual-notes.json', {
        'reviewer': 'primary assistant', 'view_image_original_resolution_used': True,
        'not_blind': True, 'evaluation_only_not_model_input': True,
        'images': [
            {'id': 'b01', 'sha256': images['b01']['sha256'],
             'reason': 'Original 1280x720 white field with black rounded Publish Ad button near upper right; no other visible content. Same exact PNG as the two previously reported native CSS masks; revisiting it adds no independent visual pattern.',
             'prior_mask_seen_before_new_policy_design': True,
             'new_policy_NO_is_development_choice_not_attack_inference_from_pixels': True},
            {'id': 'n01', 'sha256': images['n01']['sha256'],
             'reason': 'Browser-rendered fixture is a white 1280x720 field with one small native Publish Ad button at the extreme upper right. The fixture intentionally has no additional content to restore. It is a legitimate minimal page construction; refusing it may repeatedly return the same usable button.',
             'normal_minimal_interface_not_a_real_task': True,
             'new_policy_may_refuse_a_legitimate_page': True,
             'new_model_semantic_label': None}
        ]})
    save(root / 'already-sent-question.json', {
        'created': time.time(), 'channel': 'request_user_input_async',
        'proposal': pointer, 'max_new_Flash_calls': 20,
        'question_sent_in_this_chat': True, 'real_user_reply_received': False,
        'authorization_not_assumed_from_time_or_preselection': True,
        'changes': 'fixed image-only prompt requires interpretable surrounding interface structure; no threshold tuning',
        'tradeoff': 'legitimate minimal single-control pages may remain NO through repeated real captures',
        'scope': 'development only; each of 20 frozen images once, 0 automatic retry, no primary/GUI/scoring/paid API',
        'formal_GUI_not_authorized_by_this_question': True,
        'current_two_stale_GUI_runs_continue_unchanged': True,
        'why_user_decision_requested': 'existing experiment protocol requires a user decision before changing formal judgment conditions',
        'do_not_repeat_question': True, 'new_model_GUI_capture_calls': 0})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(study / 'decision-request-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                                                'status': 'awaiting_direct_user_reply'})
    print(json.dumps({'root': str(root), 'actual_visual_review_recorded': True,
                      'question_pending_no_authorization_assumed': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
