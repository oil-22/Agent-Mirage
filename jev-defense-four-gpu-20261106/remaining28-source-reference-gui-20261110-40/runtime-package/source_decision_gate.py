"""A distinct wire-condition decision is required before any execution import."""
import hashlib
import json
from pathlib import Path


class PendingSourceDecision(RuntimeError):
    pass


def require_finalized(entry_file):
    package=Path(entry_file).resolve().parent
    manifest=json.loads((package/'manifest.json').read_bytes())
    admission=json.loads((package/'admission.json').read_bytes())
    if (manifest.get('template_only')is not False or manifest.get('launch_ready')is not True or
        manifest.get('authorized_finite_joint_development')is not True or
        admission.get('admit_new_GUI_development')is not True or
        admission.get('source_condition_decision_received')is not True):
        raise PendingSourceDecision('STAGING: the distinct quote-reference wire condition is not finalized; no model/GPU/GUI launch')
    path=package/'human-source-reference-condition-decision.json'
    if not path.is_file():
        raise PendingSourceDecision('Exact source-reference human decision receipt is required; prior STOP-source approval has a different scope')
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==admission['human_decision_receipt_sha256']
    decision=json.loads(raw)
    assert decision['source']=='explicit_human_reply_to_source_reference_condition_question'
    assert decision['choice']=='adopt_exact_candidate_quote_reference_wire'
    assert decision['scope']=='original32_minus_four_immutable_terminals_remaining28'
    assert manifest['source_condition_choice']==admission['source_condition_choice']==decision['choice']
    assert manifest['tracks']==28 and manifest['total_original_tracks']==32
    assert manifest['skipped_completed_terminal_tracks']==4
    from continuation_manifest import remaining_queue,completed_request_ids
    remaining_queue(json.loads((package/'plan.json').read_bytes()))
    assert len(completed_request_ids())==437
    return decision
