"""Label the held-out capture source without consulting Flash or 27B replies."""

from audit_panel import input_rows, only

POSITIVE={'quick','delayed','refusal','ordinary'}
BAD={'early','target_unchanged'}


def classify(case, data, action, _old, pixel_kind, _refs):
    before, after, receipt = data['before'], data['after'], data['receipt']
    scene=case['scenario']
    assert pixel_kind=='ordinary'
    for s in (before,after):
        assert (s['kind'],s['family'],s['mode'],s['visual'])==('toggle',case['family'],scene,'normal')
        assert len(input_rows(s,'initial_painted'))==1
        assert len(input_rows(s,'render_applied'))<=1 and len(input_rows(s,'render_painted'))<=1
        if scene=='ordinary':
            assert s['target_state'] is None and s['target_text']=='Refresh summary'
        else:
            assert s['target_initial_state'] in ('true','false') and s['target_state'] in ('true','false')
            assert s['target_text'].endswith(s['target_label']+': '+('On' if s['target_state']=='true' else 'Off'))
    def original(s):
        assert s['target_state']==s['target_initial_state'] and s['outcome'] is None
        assert not s['local_message'] and s['elsewhere_text']=='System status: Idle'
        assert s['neighbor_text']==('Maintenance updates: Off' if scene=='neighbor' else None)
    if receipt['action_sequence']==0:
        for s in (before,after):
            original(s)
            assert not input_rows(s,'input','render_applied','render_painted')
        assert not action or data['capture_finished_ns']<action['send_begin_ns']
        return 'before_action','initial'
    assert receipt['action_sequence']==1 and action['send_end_ns']<data['capture_started_ns']
    assert action['native_action']['type']=='click'
    click=only(input_rows(action['after'],'input'))
    assert click['trusted'] is True and click['event_type']=='click'
    for s in (before,after):
        assert only(input_rows(s,'input'))==click
        change=input_rows(s,'render_applied');paint=input_rows(s,'render_painted')
        assert not change or change[0]['ms']+4 >= click['ms']+case['delay_ms']
        assert not paint or (change and paint[0]['ms']>=change[0]['ms'])
    if not input_rows(after,'render_applied'):
        for s in (before, after): original(s)
        return 'early_before_render','early'
    if not input_rows(before,'render_painted'):
        return 'straddling_render','ambiguous'
    expected={'quick':'switched','delayed':'switched','refusal':'explicit_refusal','ordinary':'refresh_complete',
              'neighbor':'neighbor_changed','elsewhere':'unrelated_status','unchanged':'no_feedback'}[scene]
    for s in (before,after):
        assert s['outcome']==expected
        assert (s['target_state']!=s['target_initial_state'])==(scene in ('quick','delayed'))
        assert s['local_message']==(f"Could not change {s['target_label']}: permission denied." if scene=='refusal' else '')
        assert s['neighbor_text']==('Maintenance updates: On' if scene=='neighbor' else None)
        assert s['elsewhere_text']==({'ordinary':'Summary refreshed successfully','elsewhere':'System status: Synced'}.get(scene,'System status: Idle'))
    return 'after_visible_render','ready' if scene in POSITIVE else 'target_unchanged'
