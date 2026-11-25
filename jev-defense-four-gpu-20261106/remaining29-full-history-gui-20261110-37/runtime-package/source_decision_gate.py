"""Refuse STAGING entry points before model, browser, resource or network imports.

Only a new, finalized package may carry an explicit human source-condition
decision. This template deliberately contains no such authorization.
"""
import hashlib
import json
from pathlib import Path


class PendingSourceDecision(RuntimeError):
    pass


def require_finalized(entry_file):
    package = Path(entry_file).resolve().parent
    manifest = json.loads((package / 'manifest.json').read_bytes())
    admission = json.loads((package / 'admission.json').read_bytes())
    if (manifest.get('template_only') is not False or
            manifest.get('launch_ready') is not True or
            manifest.get('authorized_finite_joint_development') is not True or
            admission.get('admit_new_GUI_development') is not True or
            admission.get('source_condition_decision_received') is not True):
        raise PendingSourceDecision('STAGING ONLY: source-condition choice is pending; no GPU, GUI or model launch')
    decision_path = package / 'human-source-condition-decision.json'
    if not decision_path.is_file():
        raise PendingSourceDecision('A finalized, source-bound human decision receipt is required')
    raw = decision_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == admission['human_decision_receipt_sha256']
    decision = json.loads(raw)
    assert decision['source'] == 'explicit_human_reply_to_existing_source_condition_question'
    assert decision['choice'] in ['adopt_exact_decoded_native_STOP_answer_source',
                                  'keep_original_raw_byte_source']
    assert admission['source_condition_choice'] == decision['choice']
    assert manifest['source_condition_choice'] == decision['choice']
    assert decision['scope'] == 'original32_minus_three_immutable_terminals_remaining29'
    assert manifest['tracks'] == 29 and manifest['total_original_tracks'] == 32
    from continuation_manifest import remaining_queue, completed_request_ids
    remaining_queue(json.loads((package / 'plan.json').read_bytes()))
    completed_request_ids()
    return decision
