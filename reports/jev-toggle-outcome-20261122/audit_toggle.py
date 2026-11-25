"""Read-only audit for the frozen 36-episode toggle guard comparison."""

import argparse
from collections import Counter
from pathlib import Path

from audit_panel import (chain, event, input_rows, only, timing, verify_flash,
                         verify_frames, verify_main)
from gate_core import Frame
from live_common import load, save, sha
from toggle_protocol import DISPATCH, PROBE, eligible, unpack

ARMS = ('stock', 'global046', 'scoped')
POSITIVE = {'quick', 'delayed', 'ordinary'}
KINDS = ('quality', 'temporal', 'toggle_check', 'primary')
WINDOW_CLOSED = 'post_action_observation_window_ended'


def classify(case, source, action, _first, pix, _refs):
    """Truth for the controlled fixture, without looking at either model's reply."""
    before, after, receipt = source['before'], source['after'], source['receipt']
    scene = case['scenario']
    ordinary = scene == 'ordinary'
    assert pix == 'ordinary' and case['flow'] == 'toggle'
    for s in (before, after):
        assert (s['kind'], s['family'], s['mode']) == ('toggle', case['family'], scene)
        assert s['visual'] == 'normal' and len(input_rows(s, 'initial_painted')) == 1
        assert len(input_rows(s, 'render_applied')) <= 1 and len(input_rows(s, 'render_painted')) <= 1
        if ordinary:
            assert (s['target_text'], s['target_state']) == ('Refresh report', None)
        else:
            assert s['target_state'] in ('true', 'false')
            assert s['target_text'].endswith(': ' + {'true': 'On', 'false': 'Off'}[s['target_state']])
    if receipt['action_sequence'] == 0:
        for s in (before, after):
            assert not input_rows(s, 'input', 'render_applied', 'render_painted') and s['outcome'] is None
            assert s['target_state'] == (None if ordinary else 'false')
        assert not action or source['capture_finished_ns'] < action['send_begin_ns']
        return 'before_action', 'initial'
    assert receipt['action_sequence'] == 1 and action['send_end_ns'] < source['capture_started_ns']
    assert action['native_action']['type'] == 'click'
    trusted = only(input_rows(action['after'], 'input'))
    assert trusted['trusted'] is True and trusted['event_type'] == 'click'
    for s in (before, after):
        assert only(input_rows(s, 'input')) == trusted
        flip = input_rows(s, 'render_applied')
        paint = input_rows(s, 'render_painted')
        if flip:
            assert flip[0]['ms'] + 4 >= trusted['ms'] + case['delay_ms']
        if paint:
            assert flip and flip[0]['ms'] <= paint[0]['ms']
    if not input_rows(after, 'render_applied'):
        assert before['outcome'] is after['outcome'] is None
        assert ordinary or before['target_state'] == after['target_state'] == 'false'
        return 'early_before_render', 'early'
    if not input_rows(before, 'render_painted'):
        return 'straddling_render', 'ambiguous'
    expected = {'quick': 'enabled', 'delayed': 'enabled', 'neighbor': 'other_switch_changed',
                'elsewhere': 'other_region_changed', 'unchanged': 'unchanged', 'ordinary': 'other_region_changed'}[scene]
    for s in (before, after):
        assert s['outcome'] == expected
        if scene in ('quick', 'delayed'):
            assert s['target_state'] == 'true'
        elif not ordinary:
            assert s['target_state'] == 'false'
        if scene == 'neighbor':
            assert s['neighbor_text'] == 'Reminders: On'
        if scene in ('elsewhere', 'ordinary'):
            assert s['elsewhere_text'] == 'System status: Synced'
    return 'after_visible_render', 'ready' if scene in POSITIVE else 'target_unchanged'


def checked_controls(folder, frames, action):
    """Check every signed hit record, including captures that never reached the extra check."""
    binding = load(folder / 'session.json')
    dispatch = action['toggle_dispatch'] if action else None
    click = action['native_action'] if action else None
    if action:
        d = unpack(binding, dispatch)
        assert d and d['protocol'] == DISPATCH and d['action_sequence'] == 1 and d['action'] == click
        assert all(abs(x - round(click[k] * n / 1000, 10)) < .001
                   for x, k, n in zip(d['pointer'], ('x', 'y'), binding['viewport'], strict=True))
        points = d['pointer']
    records = {}
    for cap, f in frames.items():
        data = load(folder / f"capture-{f['capture_index']:03}.json")
        signature, receipt = data['control_probe'], data['receipt']
        hit = unpack(binding, signature)
        assert hit and set(hit) == {'protocol', 'action_sequence', 'capture_id', 'image_sha256',
                                    'pointer', 'before', 'after', 'session_id', 'environment_id', 'loader', 'target'}
        assert (hit['protocol'], hit['action_sequence'], hit['capture_id'], hit['image_sha256']) == (
            PROBE, f['action_sequence'], cap, f['source_sha256'])
        if action and f['action_sequence']:
            assert hit['pointer'] == points
        raw = Path(f['candidate_png']).read_bytes() if f['candidate_png'] else None
        records[cap] = (Frame(raw, cap, 0, receipt), signature)
    return binding, click, dispatch, records


def verify_toggle_gate(case, plan, rows, frames, flash, action, old, terminal, controls):
    """Replay admission from wire evidence; source truth and labels never drive this replay."""
    assert not event(rows, 'trusted_static_boundary')
    binding, click, dispatch, records = controls
    per_frame = {}
    for row in flash:
        per_frame.setdefault(row['capture_id'], []).append(row)
    policies = event(rows, 'temporal_policy')
    routes = {r['capture_id']: r for r in policies}
    assert len(routes) == len(policies) == sum(f['kind'] == 'temporal' for f in flash)
    holds = event(rows, 'withhold_and_recapture')
    by_hold = {h['capture_id']: h for h in holds}
    assert holds == terminal['holds'] and len(by_hold) == len(holds)
    accepted_rows = event(rows, 'gate_accepted')
    accepted = {a['capture_id']: a for a in accepted_rows}
    assert len(accepted) == len(accepted_rows) == int(old is not None) + int(terminal['delivery'] is not None)
    windows = event(rows, 'study_window_started')
    assert [w['stage'] for w in windows] == (['initial', 'post_action'] if action else ['initial'])
    windows = {w['stage']: w for w in windows}
    for stage, window in windows.items():
        assert window['end_ns']-window['start_ns'] == int(plan['observation_seconds']*1e9)
        if stage == 'post_action':
            assert window['start_ns'] == action['send_end_ns']
    stops = event(rows, 'study_window_closed')
    for stop in stops:
        assert stop['fail_open'] is False and stop['end_ns'] == windows[stop['stage']]['end_ns']
        assert stop['closed_ns'] >= stop['end_ns'] or stop['status'] == 'operator_stopped'
        assert stop['status'] == terminal['status']
    assert len(stops) == int(terminal['status'].endswith('_observation_window_ended')) or terminal['status'] == 'operator_stopped'
    assert set(per_frame) | set(routes) | set(by_hold) | set(accepted) <= frames.keys()

    prior, extra_spent = None, False
    last_after_hold = None
    for cap, frame in frames.items():
        stage = 'post_action' if frame['action_sequence'] else 'initial'
        start, end = (windows[stage][k] for k in ('start_ns', 'end_ns'))
        calls = per_frame.get(cap, [])
        modes = [c['kind'] for c in calls]
        assert start <= frame['started_ns'] <= frame['finished_ns']
        if frame['finished_ns'] >= end:
            # Capture can cross the window during Chromium/receipt I/O. The
            # controller then closes it before asking Flash or delivering it.
            assert not calls and cap not in accepted and cap not in by_hold
            assert only(stops)['capture_id'] == cap and only(stops)['stage'] == stage
        if last_after_hold:
            assert last_after_hold[0] == stage and frame['started_ns'] - last_after_hold[1] >= int(plan['recapture_seconds']*1e9)
            last_after_hold = None
        now = frame['finished_ns']
        for c in calls:
            assert now <= c['started_ns'] <= c['finished_ns']
            now = c['finished_ns']
        good = frame['presence'] == frame['receipt'] == 'YES'
        proof = routes.get(cap)
        permit = good
        if not good:
            prior = None
            assert not calls and not proof
        elif stage == 'post_action':
            assert modes in ([], ['temporal'], ['temporal', 'quality'],
                             ['temporal', 'toggle_check'], ['temporal', 'toggle_check', 'quality'])
            permit = False
            if calls:
                basic = calls[0]
                assert proof and proof['standard_request_id'] == basic['request_id'] and proof['arm'] == case['arm']
                assert proof['prior_standard_request_id'] == (prior['request_id'] if prior else None)
                def gray(r):
                    return r is not None and r['decision'] == 'NO' and plan['threshold'] <= r['p_yes'] < plan['gray_upper_exclusive']
                desired = ('original_yes' if basic['decision'] == 'YES' else
                           'comparator_046' if case['arm'] == 'global046' and gray(basic) else
                           'evaluate_control_hit' if case['arm'] == 'scoped' and not extra_spent and gray(prior) and gray(basic)
                           else 'hold')
                assert proof['route'] == desired
                permit = desired in ('original_yes', 'comparator_046')
                if desired == 'evaluate_control_hit':
                    f, p = zip(*(records[k] for k in (old, prior['capture_id'], cap)), strict=True)
                    recomputed = eligible(binding, click, dispatch, f, p)
                    scope = proof['scope']
                    if scope is not None:
                        assert scope == recomputed
                    else:
                        assert cap not in accepted and not any(k in modes for k in ('toggle_check','quality'))
                    if 'toggle_check' in modes:
                        assert scope and scope['eligible'] and not extra_spent
                        extra_spent = True
                        specialist = calls[1]
                        assert specialist['request_id'] == proof['specialized_request_id']
                        permit = specialist['decision'] == 'YES'
                else:
                    assert proof['scope'] is None and 'toggle_check' not in modes
                if 'toggle_check' not in modes:
                    assert proof['specialized_request_id'] is None
                assert proof['proceed_to_quality'] is permit
                prior = basic
            else:
                assert not proof and cap not in by_hold
        else:
            assert modes in ([], ['quality']) and not proof and not prior
        quality = calls[-1] if modes and modes[-1] == 'quality' else None
        if quality:
            assert permit
        if cap in by_hold:
            hold = by_hold[cap]
            assert hold['stage'] == stage and hold['sha256'] == frame['candidate_sha'] and cap not in accepted
            assert hold['action_repeated'] is False and hold['sleep_seconds'] == plan['recapture_seconds']
            cause = ('image_presence_NO' if frame['presence'] == 'NO' else 'receipt_NO' if not good else
                     'temporal_pending_or_unsupported' if stage == 'post_action' and not permit else 'single_image_quality_NO')
            if cause == 'single_image_quality_NO':
                assert quality and quality['decision'] == 'NO'
            assert hold['reason'] == cause
            last_after_hold = stage, now
        if cap in accepted:
            a = accepted[cap]
            assert permit and quality and quality['decision'] == 'YES' and a['stage'] == stage
            assert a['quality_request_id'] == quality['request_id'] and a['window_end_ns'] == end
            assert now <= a['accepted_ns'] < end
    if old:
        assert accepted[old]['stage'] == 'initial' and accepted[old]['accepted_ns'] <= action['send_begin_ns']
    delivered = terminal['delivery']
    if delivered:
        a = accepted[delivered['capture_id']]
        assert a['stage'] == 'post_action' and a['accepted_ns'] == delivered['gate_accepted_ns']
        assert a['quality_request_id'] == delivered['last_quality_request_id']
    assert terminal['calls'] == {k: int(delivered is not None) if k == 'primary' else sum(r['kind'] == k for r in flash) for k in KINDS}
    return by_hold, routes


def verify_case(root, case, plan, template, origin, models, lease, expected=None):
    folder = root / 'run' / 'episodes' / case['id']
    source = root / 'run' / 'source' / case['id']
    terminal = load(folder / 'terminal.json')
    head, events = chain(folder / 'events.jsonl')
    assert head == terminal['journal_head'] and len(events) == terminal['events']
    assert terminal['journal_sha256'] == sha(folder / 'events.jsonl') and terminal['case'] == case
    assert events[-1]['kind'] == 'terminal' and events[-1]['data'] == {
        k: v for k, v in terminal.items() if k not in ('journal_head', 'journal_sha256', 'events')}
    if expected is not None:
        assert events[-1]['data'] == expected
    frames, action, old = verify_frames(folder, source, case, events, terminal, origin, plan['viewport'], classify=classify)
    assert terminal['session'] == only(event(events, 'session'))['session_id']
    controls = checked_controls(source, frames, action)
    replies, asked = event(events, 'flash_replied'), event(events, 'flash_requested')
    assert replies == terminal['flash']
    flash = [verify_flash(root, got, want, frames, old, action, models['flash'], lease)
             for got, want in zip(replies, asked, strict=True)]
    main, current = verify_main(root, template, case, events, terminal, frames, old, action, models['primary'], lease)
    held, policies = verify_toggle_gate(case, plan, events, frames, flash, action, old, terminal, controls)
    post = [f for f in frames.values() if f['action_sequence']]
    first = post[0] if post else None
    first_ready = next((f for f in post if f['truth'] == 'ready'), None)
    d = terminal['delivery']
    policy = policies.get(d['capture_id']) if d else None
    if current:
        assert policy and policy['proceed_to_quality'] is True
    return {'id': case['id'], 'case': case, 'session_id': terminal['session'], 'status': terminal['status'],
            'journal_head': head, 'action': action, 'initial': frames.get(old), 'frames': list(frames.values()),
            'flash': flash, 'holds': [{**h, 'truth': frames[cap]['truth']} for cap, h in held.items()],
            'policies': list(policies.values()), 'first': first, 'first_ready': first_ready,
            'first_ready_withheld': bool(first_ready and first_ready['capture_id'] in held),
            'delivery': current, 'delivery_route': policy['route'] if policy else None,
            'delivery_extra': policy['specialized_request_id'] if policy else None, 'calls': terminal['calls'],
            'post_gate_seconds': (d['gate_accepted_ns']-action['send_end_ns'])/1e9 if d else None,
            'main': main}


def verify_seal(root):
    local = load(root / 'local-seal.json')
    assert all(sha(root / name) == digest for name, digest in local.items())
    remote, manifest = load(root / 'remote-seal.json'), load(root / 'manifest.json')
    assert manifest['name'] == root.name and remote['input_manifest_sha256'] == local['manifest.json']
    assert all(local[n] == digest for n, digest in manifest['files'].items())
    assert {n: h for n, h in local.items() if n.startswith('run/')} == remote['files']
    assert {p.relative_to(root).as_posix() for p in (root / 'run').rglob('*') if p.is_file()} == set(remote['files'])
    return manifest, remote


def verify_origin(root):
    origin = load(root / 'run' / 'source' / 'source.json')
    assert origin['fixture_sha256'] == sha(root / 'fixture.html') and origin['source_code_sha256'] == sha(root / 'capture_gui.py')
    assert origin['source']['uid'] == origin['browser']['uid'] == 1033
    assert origin['debug_transport'] == 'inherited anonymous pipes (no listener)'
    assert origin['source']['cmdline'][-1].endswith('/'+root.name+'/capture_gui.py')
    argv = ' '.join(origin['browser']['cmdline']).split()
    assert '--remote-debugging-pipe' in argv and not any(x.startswith('--remote-debugging-port') for x in argv)
    assert any(x.endswith('/'+root.name+'/browser-profile') and x.startswith('--user-data-dir=') for x in argv)
    return origin


def audit_capture_preflight(root):
    manifest, remote = verify_seal(root)
    assert manifest['mode'] == 'capture-preflight' and remote['exit_status'] == 0
    plan = load(root / 'live_plan.json')
    terminal, origin = load(root / 'run' / 'terminal.json'), verify_origin(root)
    assert terminal['status'] == 'passed' and terminal['source_worker_exit'] == 0
    assert terminal['gpu_allocations'] == terminal['new_model_calls'] == 0
    assert [r['case']['id'] for r in terminal['completed']] == manifest['preflight_ids'] and len(manifest['preflight_ids']) == 8
    output = []
    for row in terminal['completed']:
        case = only(r for r in plan['cases'] if r == row['case'])
        folder = root / 'run' / 'episodes' / case['id']
        source = root / 'run' / 'source' / case['id']
        head, events = chain(folder / 'events.jsonl')
        t = load(folder / 'terminal.json')
        assert (head, len(events), sha(folder / 'events.jsonl')) == (t['journal_head'], t['events'], t['journal_sha256'])
        assert events[-1]['kind'] == 'terminal' and events[-1]['data'] == row
        classified, action, old = verify_frames(folder, source, case, events, {**t, 'native_action': load(source / 'action.json')['native_action'],
                                                                                 'subsequent_action_executed': False},
                                                origin, plan['viewport'], classify=classify)
        bind, click, dispatch, records = checked_controls(source, classified, action)
        assert old == next(iter(classified))
        f, p = zip(*(records[k] for k in (old, *list(classified)[-2:])), strict=True)
        proof = eligible(bind, click, dispatch, f, p)
        assert proof['eligible'] == (case['scenario'] in {'quick', 'delayed'})
        output.append({'id': case['id'], 'frames': list(classified.values()), 'scope': proof})
    assert load(root / 'run' / 'source' / 'exit.json') == {'browser_exit': 0, 'identity': origin['browser']}
    return {'status': 'capture_only_passed', 'frames': sum(len(r['frames']) for r in output), 'episodes': output}


def audit_ownership(root, manifest, plan, top):
    run = root / 'run'
    lease = load(run / 'gpu-lease.json')
    assert lease['holder']['uid'] == 1033 and lease['holder']['cmdline'] == [manifest['python'], '-B', '-u', 'live_run.py']
    assert (lease['roles']['primary']['physical'], lease['roles']['flash']['physical']) == (plan['primary_physical_gpus'], [plan['flash_physical_gpu']])
    uuids = [u for r in lease['roles'].values() for u in r['uuids']]
    keys = {x['path'] for x in lease['locks']}
    assert len(lease['locks']) == len(keys) == 12 and len(uuids) == len(set(uuids)) == 5
    assert all(sum(p.endswith('/'+u+'.lock') for p in keys) == 2 for u in uuids)
    for snap in (lease['smi_before'], lease['smi_after']):
        assert not snap['compute'] and min(c['free_mib'] for c in snap['cards'].values()) >= 23000
        for role in lease['roles'].values():
            assert role['uuids'] == [snap['cards'][str(k)]['uuid'] for k in role['physical']]
    models = {r: load(run / r / 'loaded.json') for r in ('flash', 'primary')}
    for role, m in models.items():
        exe = manifest['python'] if role == 'primary' else load(root / 'service-config.json')['python']
        uid, argv = (m['process'][k] for k in ('uid', 'cmdline'))
        assert uid == 1033 and argv[:-2] == [exe, '-B', '-u'] and argv[-2].endswith('/'+root.name+'/live_models.py') and argv[-1] == role
        assert m['BF16'] is True and m['native_sdpa' if role == 'flash' else 'SDPA'] is True
        compute = m['compute']
        assert compute['lock_owner'] == lease['holder'] and compute['uuids'] == lease['roles'][role]['uuids']
        assert {r['uuid'] for r in compute['compute']} == set(compute['uuids'])
        assert all(r['process'] == m['process'] for r in compute['compute'])
    assert models['primary']['model'] == load(root / 'primary-reference.json')['primary_model']
    assert models['primary']['placement'] == load(root / 'four-card-placement.json')
    assert models['flash']['revision'] == plan['revision'] and models['flash']['fast'] is False
    release = load(run / 'gpu-release.json') if (run / 'gpu-release.json').is_file() else None
    if release:
        assert [(r['path'],r['inode']) for r in release['locks']] == [(r['path'],r['inode']) for r in lease['locks']]
        assert all(r['state'] in ('released_verified','acquired_by_another_process_after_release') for r in release['locks'])
        assert set(release['closed_worker_pids']) == {m['process']['pid'] for m in models.values()}
        assert {a['pid'] for a in release['snapshot']['compute']}.isdisjoint(release['closed_worker_pids'])
    if top['status'] == 'completed_panel':
        assert release and top['closed_workers'] == {'primary': 0, 'flash': 0, 'browser': 0}
    return lease, models, release


def outcome(row):
    return (row.get('delivery') or {}).get('truth')


def contextual_summary(episodes):
    good = [r for r in episodes if r['case']['scenario'] in POSITIVE]
    faults = [r for r in episodes if (r['first'] or {}).get('truth') in ('early','target_unchanged')]
    calls = [f for r in episodes for f in r['flash']]
    scoped = [p for r in episodes for p in r['policies'] if p['route'] == 'evaluate_control_hit']
    return {
        'episodes': len(episodes), 'normal_action_cases': len(good),
        'normal_action_ready_delivered': sum(outcome(r) == 'ready' for r in good),
        'normal_action_with_a_ready_capture': sum(r['first_ready'] is not None for r in good),
        'first_ready_frame_withheld': sum(r['first_ready_withheld'] for r in good),
        'normal_action_censored': sum(r['status'] == WINDOW_CLOSED for r in good),
        'first_bad_frame_observed': len(faults),
        'first_bad_frame_explicitly_held': sum(any(x['capture_id'] == r['first']['capture_id'] for x in r['holds']) for r in faults),
        'first_bad_held_then_ready_delivered': sum(outcome(r) == 'ready' and any(x['capture_id'] == r['first']['capture_id'] for x in r['holds']) for r in faults),
        'bad_frame_delivered': sum(outcome(r) in ('early','target_unchanged') for r in episodes),
        'ambiguous_frame_delivered': sum(outcome(r) == 'ambiguous' for r in episodes),
        'no_post_delivery': sum(r['delivery'] is None for r in episodes),
        'main_results': sum(r['main'] is not None for r in episodes),
        'natural_eos': sum(bool(r['main'] and r['main']['natural_eos']) for r in episodes),
        'temporal_gray_NO_calls': sum(f['kind']=='temporal' and f['decision']=='NO' and .46 <= f['p_yes'] < .5 for f in calls),
        'scope_evaluations': sum(p['scope'] is not None for p in scoped),
        'scope_passes': sum(bool(p['scope'] and p['scope']['eligible']) for p in scoped),
        'scope_rejection_reasons': dict(Counter(p['scope']['reason'] for p in scoped if p['scope'] and not p['scope']['eligible'])),
        'specialized_yes': sum(f['kind']=='toggle_check' and f['decision']=='YES' for f in calls),
        'specialized_no': sum(f['kind']=='toggle_check' and f['decision']=='NO' for f in calls),
        'extra_deliveries': sum(r['delivery_extra'] is not None for r in episodes),
        'ready_action_to_delivery': timing([r['post_gate_seconds'] for r in good if outcome(r)=='ready']),
        'flash_native_seconds': round(sum(f['native_seconds'] for f in calls), 3),
        'primary_native_seconds': round(sum(r['main']['seconds'] for r in episodes if r['main']), 3),
    }


def compare(episodes, groups):
    bad = {'early', 'target_unchanged'}
    by_key = {(r['case']['group'], r['case']['arm']): r for r in episodes}
    pairs = []
    for group in sorted(groups):
        p = {a: by_key.get((group, a)) for a in ARMS}
        a, b, c = (p[k] for k in ARMS)
        shown = [r for r in p.values() if r is not None]
        comparable = (len(shown) == 3 and all(r['action'] and r['initial'] for r in shown)
                      and len({r['initial']['candidate_sha'] for r in shown}) == 1
                      and all(r['action']['native_action'] == a['action']['native_action'] for r in shown))
        outcomes = {i: outcome(r) if r else 'unreviewed' for i, r in p.items()}
        ambiguous = 'ambiguous' in outcomes.values()
        def repeat_ready(row):
            if not comparable or not row or a['status'] != WINDOW_CLOSED or outcome(row) != 'ready':
                return False
            withholds = {r['sha256'] for r in a['holds'] if r['truth'] == 'ready'}
            return row['delivery']['candidate_sha'] in withholds
        pairs.append({'group': group, 'comparable_by_same_initial_png_and_native_action': comparable,
                      'ambiguous_delivery': ambiguous, 'outcomes': outcomes,
                      'stock_first_ready_withheld': a['first_ready_withheld'] if a else None,
                      'stock_ready_censored_scoped_ordinary_recovery': bool(repeat_ready(c) and not c['delivery_extra']),
                      'stock_ready_censored_scoped_targeted_recovery': bool(repeat_ready(c) and c['delivery_extra']),
                      'stock_ready_censored_global_recovery': repeat_ready(b),
                      'new_scoped_bad_delivery': comparable and outcomes['scoped'] in bad and outcomes['stock'] not in bad,
                      'new_global_bad_delivery': comparable and outcomes['global046'] in bad and outcomes['stock'] not in bad,
                      'preexisting_stock_bad_delivery': comparable and outcomes['stock'] in bad})
    return pairs


def audit_live(root):
    manifest, remote = verify_seal(root)
    run = root / 'run'
    plan, template = load(root / 'live_plan.json'), load(root / 'actor-template.json')
    assert manifest['mode'] == 'live' and manifest['retries_of_model_or_action'] == 0
    assert manifest['max_primary_calls'] == plan['max_primary_calls'] == len(plan['cases']) == 36
    assert plan['cases_by_arm'] == dict.fromkeys(ARMS, 12)
    assert (plan['threshold'], plan['gray_upper_exclusive'], plan['max_extra_requests_per_action']) == (.46, .5, 1)
    assert set(plan['cases_by_arm']) == set(ARMS) and len({c['id'] for c in plan['cases']}) == 36
    ref = root.parent / manifest['capture_preflight']
    assert manifest['preflight_seal_sha256'] == sha(ref / 'local-seal.json')
    pre, _ = verify_seal(ref)
    assert all(manifest['files'][n] == digest for n,digest in pre['files'].items())
    if manifest['parent_if_technical_retry']:
        parent = root.parent / manifest['parent_if_technical_retry']
        assert manifest['technical_failure_parent_seal'] == sha(parent / 'local-seal.json')
        _, failed = verify_seal(parent)
        assert failed['exit_status'] != 0 and load(parent / 'run' / 'terminal.json')['status'] == 'technical_failure'
        assert not list((parent/'run'/'source').glob('*/action.json')) and not list((parent/'run').glob('*/*/start.json'))
    top = load(run / 'terminal.json')
    assert top['planned_episodes'] == 36 and top['official_score_calls'] == top['paid_API_calls'] == top['old_queues_launched'] == 0
    ended = top['status'] == 'completed_panel'
    finished = {s['case']['id']: s for s in top['sessions']}
    assert len(finished) == len(top['sessions']) and list(finished) == [c['id'] for c in plan['cases'][:len(finished)]]
    if ended:
        assert len(finished) == top['attempted_episodes'] == 36 and not top['error'] and remote['exit_status'] == 0
        assert set(finished) == {p.name for p in (run / 'episodes').iterdir() if p.is_dir()}
    origin = verify_origin(root)
    lease, models, release = audit_ownership(root, manifest, plan, top)
    if ended:
        assert load(run / 'source' / 'exit.json') == {'browser_exit': 0, 'identity': origin['browser']}
    summaries, counters = [], Counter(dict.fromkeys(KINDS, 0))
    requests, caps, sessions = {'primary': set(), 'flash': set()}, set(), set()
    for case in plan['cases']:
        if case['id'] not in finished:
            continue
        row = verify_case(root, case, plan, template, origin, models, lease, finished[case['id']])
        captures = {f['capture_id'] for f in row['frames']}
        assert not caps & captures and row['session_id'] not in sessions
        caps |= captures
        sessions.add(row['session_id'])
        for role, values in (('flash', row['flash']), ('primary', [row['main']] if row['main'] else [])):
            for v in values:
                assert v['request_id'] not in requests[role]
                requests[role].add(v['request_id'])
        counters.update(row['calls'])
        summaries.append(row)
    assert dict(counters) == top['completed_sessions_call_counts']
    raw = {role: {part: {p.parent.name for p in (run / role).glob('*/' + part + '.json')} for part in ('start', 'result')}
           for role in requests}
    if ended:
        assert all(raw[r]['start'] == raw[r]['result'] == requests[r] for r in requests)
    pairs = compare(summaries, {c['group'] for c in plan['cases']})
    recovery = [p['group'] for p in pairs if p['stock_ready_censored_scoped_targeted_recovery']]
    adverse = [p['group'] for p in pairs if p['new_scoped_bad_delivery']]
    unresolved = [p['group'] for p in pairs if not p['comparable_by_same_initial_png_and_native_action'] or p['ambiguous_delivery']]
    return {'attempt': root.as_posix(), 'status': top['status'], 'error': top['error'],
            'all_raw_sha256_seal': sha(root / 'local-seal.json'), 'audit_code_sha256': sha(__file__),
            'audited_episodes': len(summaries), 'signed_captures': len(caps), 'journal_heads': len(summaries),
            'models': models, 'release': release, 'browser_origin': origin, 'lease': lease,
            'model_calls': dict(counters), 'model_records': {r: {k: len(v) for k,v in m.items()} for r,m in raw.items()},
            'by_arm': {a: contextual_summary([r for r in summaries if r['case']['arm']==a]) for a in ARMS},
            'pairs': pairs, 'episodes': summaries,
            'qualification_pending_visual_review': {'passes_source_and_wire': bool(ended and recovery and not adverse and not unresolved),
                'recovered_groups': recovery, 'new_bad_groups': adverse, 'unresolved_groups': unresolved}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--preflight', action='store_true')
    cli = parser.parse_args()
    result = (audit_capture_preflight if cli.preflight else audit_live)(cli.attempt.resolve())
    save(cli.out, result)
    print(result['status'])
    if not cli.preflight:
        print(result['model_calls'], result['qualification_pending_visual_review'])
