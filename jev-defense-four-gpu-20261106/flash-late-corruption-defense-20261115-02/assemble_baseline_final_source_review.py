"""Bind already read notes to the final complete baseline source; no inference."""
import hashlib
import json
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    run = 'late15-T089-late_blur3-baseline'
    target = HERE/'manual-T089-blur-baseline-final-annotations.json'
    assert not target.exists()
    final_pointer, root = checked(HERE/('source-packets-'+run+'-current.json'))
    rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
    prior_pointer = HERE/'T089-blur-baseline-prefix15-source-review-current.json'
    prior, prior_root = checked(prior_pointer)
    assert len(json.loads((prior_root/'review.json').read_bytes())['candidate_labels']) == 15
    definitions = [
        (16,25,'manual-T089-blur-baseline-prefix16-25-source-notes.json',25),
        (26,35,'manual-T089-blur-baseline-prefix26-35-source-notes.json',35),
        (36,40,'manual-T089-blur-baseline-prefix36-40-source-notes.json',40),
    ]
    annotations, viewed, bindings = [], set(), []
    for start, end, filename, count in definitions:
        path = HERE/filename
        note = json.loads(path.read_bytes())
        pp, pr = checked(HERE/(f'source-prefix-{run}-{count}-current.json'))
        if 'source_prefix_pointer' in note:
            assert note['source_prefix_pointer'] == pp
        prefix = json.loads((pr/'actor.json').read_bytes())['result']['requests']
        assert len(prefix) == count
        assert prefix == rows[:count], 'Full current/legal histories must match'
        current_viewed = {r['current_image_sha256'] for r in rows[start-1:end]}
        assert set(note['viewed_original_current_PNG_sha256s']) == current_viewed
        viewed.update(current_viewed)
        positives = set(note['definite_visual_Mirage'])
        unresolved = set(note.get('unresolved_subclaims',[]))
        for decision in range(start,end+1):
            text = note['notes'][str(decision)]
            if decision == 16:
                text += ' triple-click是未来计划，单次click可为第一步；未据此认定已执行错误动作。'
            annotations.append({'decision':decision,
                'definite_boundary_inclusive_Mirage':decision in positives,
                'has_unresolved_subclaim':decision in unresolved,
                'pure_native_WAIT_excluded':False,
                'separate_native_action_error':False, 'source_review':text})
        bindings.append({'notes_file':filename,'notes_sha256':sha(path),'exact_final_source_prefix':pp})
    tail_path = HERE/'manual-T089-blur-baseline-prefix41-final-source-notes.json'
    tail = json.loads(tail_path.read_bytes())
    assert tail['source_packets'] == final_pointer
    assert [v['decision'] for v in tail['candidate_annotations']] == list(range(41,len(rows)+1))
    assert set(tail['viewed_original_current_PNG_sha256s']) == {r['current_image_sha256'] for r in rows[40:]}
    viewed.update(tail['viewed_original_current_PNG_sha256s'])
    annotations.extend(tail['candidate_annotations'])
    assert [v['decision'] for v in annotations] == list(range(16,len(rows)+1))
    save(target, {'run_id':run,'previous_review_pointer':str(prior_pointer),
        'candidate_annotations':annotations,'viewed_original_current_PNG_sha256s':sorted(viewed),
        'source_limitations_and_notes':{
            'prefix_source_notes_and_exact_final_match':bindings,
            'tail_notes_sha256':sha(tail_path),'first15_reused_only_after_exact_source_binding':prior,
            'pure_native_WAIT_excluded':True,'future_multiaction_plans_not_completed_facts':True,
            'single_reviewer_selected_development_not_fully_blind':True,
            'qualified_may_display_lag_not_automatically_definite_Mirage':True,
            'visual_transcription_arithmetic_native_action_strategy_separate':True,
            'postexit_raw_audit_separate':True}})
    print(json.dumps({'annotations':str(target),'candidates':len(rows),'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
