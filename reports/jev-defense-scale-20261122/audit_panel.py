"""Audit sealed scale-run evidence without access to a live model or gate."""

import argparse
import base64
from functools import lru_cache
import io
import json
import math
from pathlib import Path
import sqlite3
from statistics import median, quantiles
import struct

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from PIL import Image

from live_common import canonical, hash_bytes, load, save, sha
from temporal_request import native_request

FAULT = {'early', 'white', 'buttons', 'missing', 'replaced'}
READY = {'ready', 'boundary'}
OUTCOMES = {'search': 'results', 'type': 'filled', 'pagination': 'page2',
            'open': 'dialog_open', 'toggle': 'enabled', 'escape': 'dialog_closed'}


def only(rows):
    result, = rows
    return result


def event(rows, kind):
    return [row['data'] for row in rows if row['kind'] == kind]


def chain(path):
    head = '0' * 64
    out = []
    for i, raw in enumerate(path.read_bytes().splitlines()):
        row = json.loads(raw)
        assert row['seq'] == i and row['previous'] == head
        head = row.pop('sha256')
        assert head == hash_bytes(canonical(row))
        out.append({**row, 'sha256': head})
    return head, out


def unurl(url):
    prefix = 'data:image/png;base64,'
    assert url.startswith(prefix)
    return base64.b64decode(url[len(prefix):], validate=True)


def shape_and_interim(raw):
    with Image.open(io.BytesIO(raw)) as png:
        assert png.format == 'PNG' and png.n_frames == 1
        white = png.convert('RGB')
        ink = white.point([255] * 255 + [0] + [255] * 255 + [0] + [255] * 255 + [0]).getbbox()
        if ink is None:
            return png.size, 'white'
        l, t, r, b = ink
        if 40 < r-l < 150 and 25 < b-t < 70 and l > 530 and r < 750 and t > 310 and b < 410:
            return png.size, 'buttons'
        return png.size, 'ordinary'


def input_rows(snapshot, *kinds):
    return [e for e in snapshot['events'] if e['kind'] in kinds]


def dimensions(snapshot):
    return tuple(snapshot[k] for k in ('scroll_top', 'client_height', 'scroll_height', 'scroll_width', 'client_width'))


def is_boundary(origin, action, first, raw_sha):
    a, b = origin['before'], origin['after']
    wheel = only(input_rows(b, 'wheel'))
    return (action['native_action'] == {'type': 'scroll', 'direction': 'down'} and wheel['trusted'] and wheel['delta_y'] > 0
            and dimensions(a) == dimensions(b) and a['scroll_top'] > 0
            and a['scroll_top'] + a['client_height'] == a['scroll_height'] and raw_sha == first['candidate_sha'])


def escape_references(run, plan):
    """Same-family, browser-confirmed closed-dialog PNGs; no model outputs used."""
    refs = {}
    for c in plan['cases']:
        if c['flow'] != 'escape' or c['arm'] != 'fast':
            continue
        folder = run / 'source' / c['id']
        for p in sorted(folder.glob('capture-*.json')):
            src = load(p)
            if src['receipt']['action_sequence'] != 1:
                continue
            a, b = src['before'], src['after']
            if a['outcome'] == b['outcome'] == 'dialog_closed' and input_rows(a, 'render_painted'):
                h = src['receipt']['image_sha256']
                assert sha(folder / 'originals' / (h + '.png')) == h
                refs.setdefault(c['family'], set()).add(h)
    return refs


def read_truth(case, origin, action, first, pix, escaped_ready):
    before, after, r = origin['before'], origin['after'], origin['receipt']
    for snapshot in (before, after):
        assert (snapshot['kind'], snapshot['family'], snapshot['mode']) == (case['flow'], case['family'], case['scenario'])
        assert len(input_rows(snapshot, 'initial_painted')) == 1
    if r['action_sequence'] == 0:
        assert not input_rows(after, 'input', 'wheel', 'render_applied') and after['visual'] == 'normal' and pix != 'white'
        if action:
            assert origin['capture_finished_ns'] < action['send_begin_ns']
        return 'before_action', 'initial'
    assert r['action_sequence'] == 1 and action and action['send_end_ns'] < origin['capture_started_ns']
    if case['flow'] == 'boundary':
        return 'boundary_candidate', 'boundary' if is_boundary(origin, action, first, r['image_sha256']) else 'ambiguous'
    for snap in (before, after):
        trusted = only(input_rows(snap, 'input'))
        assert trusted['trusted'] and trusted == only(input_rows(action['after'], 'input'))
        if case['flow'] == 'type':
            assert action['native_action'] == {'type': 'type', 'text': trusted['value']}
        elif case['flow'] == 'escape':
            assert action['native_action'] == {'type': 'press', 'key': 'Escape'} and trusted['event_type'] == 'cancel'
        else:
            assert action['native_action']['type'] == 'click' and trusted['event_type'] == 'click'
    if not input_rows(after, 'render_applied'):
        expect = case['scenario']
        assert before['outcome'] is None and after['outcome'] is None
        if expect in ('white', 'buttons'):
            assert before['visual'] == after['visual'] == expect and pix == expect
            return 'early_before_render', expect
        assert before['visual'] == after['visual'] == 'normal' and pix == 'ordinary'
        if case['flow'] == 'escape':
            same_png = r['image_sha256'] == first['candidate_sha']
            ready_png = r['image_sha256'] in escaped_ready
            # Chromium native dialog handling can finish before the scripted
            # callback. Matching original PNGs settles the visual state.
            assert not (same_png and ready_png)
            return 'early_before_render', 'early' if same_png else 'ready' if ready_png else 'ambiguous'
        return 'early_before_render', 'early'
    if input_rows(before, 'render_painted'):
        assert before['visual'] == after['visual'] == 'normal'
        assert before['outcome'] == after['outcome'] == OUTCOMES[case['flow']]
        assert pix != 'white' and (pix != 'buttons' or case['scenario'] == 'sparse')
        if case['flow'] == 'type':
            assert before['entered'] == after['entered'] == action['native_action']['text']
        applied = only(input_rows(before, 'render_applied'))['ms']
        assert applied + 4 >= only(input_rows(before, 'input'))['ms'] + case['delay_ms']
        assert applied <= only(input_rows(before, 'render_painted'))['ms']
        return 'after_visible_render', 'ready'
    return 'straddling_render', 'ambiguous'


def verify_frames(folder, source, case, rows, terminal, origin_proof, viewport, escaped_ready=()):
    binding = load(source / 'session.json')
    final = load(source / 'finish.json')
    assert only(event(rows, 'session')) == binding and terminal['finish'] == final
    assert (binding['session_id'], binding['environment_id'], binding['loader']) == (
        final['session_id'], final['environment_id'], final['loader'])
    assert origin_proof['target'] == binding['target'] and origin_proof['source_code_sha256'] == binding['source_code_sha256']
    dispatched = final['dispatch_calls']
    assert dispatched in (0, 1)
    observed = input_rows(final['final_dom'], 'input', 'wheel')
    assert len(observed) == dispatched and all(e['trusted'] for e in observed)
    action = load(source / 'action.json') if dispatched else None
    assert event(rows, 'actual_native_action') == ([action] if action else [])
    if action:
        assert action['dispatch_calls'] == action['action_sequence'] == 1
        assert (action['environment'], action['loader'], action['target']) == (
            binding['environment_id'], binding['loader'], binding['target'])
    else:
        assert not (source / 'action.json').exists()
    assert terminal['native_action'] == (action['native_action'] if action else None)
    assert terminal['subsequent_action_executed'] is False

    ledger_path = folder / 'challenges.sqlite'
    assert not ledger_path.with_suffix('.sqlite-wal').exists()
    with sqlite3.connect(ledger_path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        led = {r[0]: r[1:] for r in db.execute('select challenge,sequence,issued_ns,state,reason,closed_ns from challenges')}
        persisted, = db.execute('select value from binding where id = 1').fetchone()
        assert json.loads(persisted) == {k: binding[k] for k in ('public_key', 'session_id', 'environment_id', 'source_code_sha256')}
    public = bytes.fromhex(binding['public_key'])
    pub = Ed25519PublicKey.from_public_bytes(public)
    time_order = event(rows, 'capture')
    receipt_rows, presence_rows = event(rows, 'receipt'), event(rows, 'presence')
    assert len(time_order) == len(receipt_rows) == len(presence_rows) == len(led) == final['capture_count']
    stored, faults = {}, []
    initial_acceptance = event(rows, 'initial_accepted')
    assert len(initial_acceptance) == dispatched
    accepted_id = initial_acceptance[0]['capture_id'] if dispatched else None
    for idx, (r, p, c, f) in enumerate(zip(receipt_rows, presence_rows, time_order, terminal['frames'], strict=True), 1):
        signed = r['receipt']
        assert signed['capture_index'] == f['capture_index'] == idx
        capture_id, source_sha = signed['capture_id'], signed['image_sha256']
        assert capture_id == p['capture_id'] == r['capture_id'] == c['capture_id'] == f['capture_id'] and capture_id not in stored
        where = load(source / f'capture-{idx:03}.json')
        assert where['receipt'] == signed and where['scope'] == case['id'] and where['constituent_source'] == 'Page.captureScreenshot'
        assert (where['target'], where['loader']) == (binding['target'], binding['loader'])
        assert signed['protocol'] == 'trusted-native-capture-ed25519-v1' and signed['key_id'] == hash_bytes(public)
        assert all(signed[key] == binding[key] for key in ('session_id', 'environment_id', 'source_code_sha256'))
        pub.verify(bytes.fromhex(signed['signature']), canonical({k: v for k, v in signed.items() if k != 'signature'}))
        challenge = signed['challenge']
        sequence, issued_ns, state, why, closed_ns = led[challenge]
        assert r['expected'] == {'challenge': challenge, 'environment_id': binding['environment_id'], 'action_sequence': sequence}
        assert sequence == signed['action_sequence'] == f['action_sequence'] and issued_ns <= signed['acquired_at_ns'] <= closed_ns
        assert where['capture_started_ns'] == f['started_ns'] <= f['finished_ns'] == where['capture_finished_ns']
        if stored:
            assert next(reversed(stored.values()))['finished_ns'] < where['capture_started_ns']
        original_png = (source / 'originals' / (source_sha + '.png')).read_bytes()
        assert source_sha == f['source_sha256'] == hash_bytes(original_png)
        size, pix = shape_and_interim(original_png)
        assert tuple(viewport) == size
        digest = c['image_sha256']
        candidate_path = folder / (digest + '.png') if digest else None
        if candidate_path:
            assert sha(candidate_path) == digest
        fault = f['transport_fault']
        assert digest == f['sha256']
        physical_phase, physical_truth = read_truth(case, where, action, stored.get(accepted_id), pix, escaped_ready)
        assert physical_phase == f['phase_after_the_fact']
        if fault:
            assert fault == case['scenario'] in ('missing', 'replaced') and sequence == 1
            assert not any(s['action_sequence'] == 1 for s in stored.values())
            faults.append({'kind': fault, 'capture_id': capture_id, 'source_sha256': source_sha,
                           'candidate_sha256': digest, 'receipt_kept_unchanged': True, 'sequence': sequence})
        if fault == 'missing':
            assert digest is None and (p['value'], p['reason'], p['byte_length']) == ('NO', 'missing_image', 0)
            expected = ('rejected', 'missing_image', 'NO')
        elif fault == 'replaced':
            assert digest != source_sha and digest == stored[accepted_id]['candidate_sha']
            expected = ('rejected', 'capture_bytes_replaced', 'NO')
        else:
            assert digest == source_sha and candidate_path.read_bytes() == original_png
            expected = ('accepted', 'receipt_bound_proceed_to_Flash', 'YES')
        if digest:
            assert (p['value'], p['reason'], p['byte_length']) == ('YES', 'image_data_present', candidate_path.stat().st_size)
        assert (state, why, r['decision']['value']) == expected
        assert (f['presence'], f['receipt'], f['receipt_reason']) == (p['value'], expected[-1], why)
        basis = ('byte-identical to independently painted same-family fast Escape control'
                 if case['flow'] == 'escape' and physical_phase == 'early_before_render' and physical_truth == 'ready'
                 else None)
        stored[capture_id] = {**f, 'truth': fault or physical_truth, 'source_truth': physical_truth, 'candidate_sha': digest,
                              'visual_label_override_reason': basis,
                              'acquisition_png': (source / 'originals' / (source_sha + '.png')).as_posix(),
                              'candidate_png': candidate_path.as_posix() if candidate_path else None,
                              's_after_action': (f['finished_ns']-action['send_end_ns'])/1e9 if sequence else None}
    assert event(rows, 'candidate_transport_fault') == faults
    if dispatched:
        assert stored[accepted_id]['truth'] == 'initial' and stored[accepted_id]['candidate_sha'] == initial_acceptance[0]['sha256']
    return stored, action, accepted_id


def verify_admission(d, model_state, lease, role):
    start = load(d / 'start.json')
    ownership = start['owned_compute']
    assert ownership['lock_owner'] == lease['holder']
    assert ownership['uuids'] == lease['roles'][role]['uuids']
    assert {x['uuid'] for x in ownership['compute']} == set(ownership['uuids'])
    assert all(x['process'] == model_state['process'] and x['pid'] == model_state['process']['pid'] for x in ownership['compute'])
    assert ownership['observed_at_ns'] <= start['at_ns']


@lru_cache
def probability_temperature(root):
    source = Path(__file__).resolve().parent / 'flash-native-audit-source'
    provenance = load(source / 'source-seal.json')
    actual = load(root / 'run' / 'flash' / 'checkpoint-before.json')
    assert provenance['revision'] == actual['revision']
    source_hashes = {f['file']: f['sha256_from_completed_byte_audit'] for f in actual['files']}
    assert all(sha(source / n) == h == source_hashes[n] for n, h in provenance['files'].items())
    return load(source / 'decision_config.json')['temperature']


def verify_flash(root, row, requested, frames, old_id, action, model, lease):
    d = root / 'run' / 'flash' / row['request_id']
    result, wire = load(d / 'result.json'), load(d / 'wire.json')
    native, inputs = load(d / 'native-request.json'), load(d / 'expected-inputs.json')
    actual = load(d / 'actual-forward.json')
    verify_admission(d, model, lease, 'flash')
    assert actual['past_key_values'] is None and actual['use_cache'] is False
    assert actual['tensors_per_forward'] == [inputs['tensors']] and len(actual['native_readout']) == 1
    assert inputs['tensors']['image_grid_thw']['shape'] == [len(row['images']), 3]
    assert len(inputs['ordered_pixel_slices']) == len(row['images'])
    ids = only(inputs['tensors']['input_ids']['values'])
    assert ids_sha(ids) == inputs['tensors']['input_ids']['sha256']
    grid = inputs['tensors']['image_grid_thw']['values']
    assert all(math.prod(row) == s['shape'][0] for row, s in zip(grid, inputs['ordered_pixel_slices'], strict=True))
    assert result['wire_sha256'] == row['wire_sha256'] == sha(d / 'wire.json')
    assert row['forward_sha256'] == result['forward_sha256'] == sha(d / 'actual-forward.json')
    assert result['native_request_sha256'] == sha(d / 'native-request.json')
    assert requested == {k: row[k] for k in ('request_id', 'kind', 'capture_id', 'wire_sha256', 'images')}
    assert result['request_id'] == wire['request_id'] == row['request_id'] and result['kind'] == row['kind'] == wire['kind']
    assert result['revision'] == model['revision']
    current = frames[row['capture_id']]
    assert current['presence'] == current['receipt'] == 'YES'
    body = wire['body']
    if wire['kind'] == 'quality':
        assert set(body) == {'image_png_base64', 'image_sha256', 'request_id'}
        assert body['request_id'] == wire['request_id']
        raw = base64.b64decode(body['image_png_base64'], validate=True)
        assert body['image_sha256'] == hash_bytes(raw) and raw == Path(current['candidate_png']).read_bytes()
        contract = load(root / 'gate-contract.json')
        assert result['quality_contract_sha256'] == sha(root / 'gate-contract.json')
        assert native['state'] == contract['state']
        question = 'usable'
        assert native['questions'] == {question: {'type': 'choice', 'instructions': contract['question'], 'criteria': contract['options']}}
        option_names = list(contract['options'])
        hashes = [current['candidate_sha']]
    else:
        assert wire['kind'] == 'temporal' and set(body) == {'previous', 'action', 'current'}
        assert current['action_sequence'] == 1 and action and body['action'] == action['native_action']
        assert result['quality_contract_sha256'] is None
        prev, raw = unurl(body['previous']), unurl(body['current'])
        assert prev == Path(frames[old_id]['candidate_png']).read_bytes() and raw == Path(current['candidate_png']).read_bytes()
        wanted = native_request(prev, action['native_action'], raw)
        wanted['images'] = [{'sha256': hash_bytes(prev)}, {'sha256': hash_bytes(raw)}]
        assert native == wanted
        question = 'action_outcome_visible'
        option_names = list(wanted['questions'][question]['criteria'])
        hashes = [frames[old_id]['candidate_sha'], current['candidate_sha']]
    assert hashes == row['images'] == result['ordered_images'] == [image['sha256'] for image in native['images']]
    p = result['probabilities']
    answer = result['native_result']['answers']
    assert set(answer) == {question} and answer[question]['probabilities'] == p
    assert set(p) == {'YES', 'NO'} and all(0.0 <= v <= 1.0 for v in p.values()) and abs(sum(p.values())-1) < 1e-6
    logits = only(only(actual['native_readout']))[:len(option_names)]
    scores = [math.exp((x-max(logits))/probability_temperature(root)) for x in logits]
    assert all(math.isclose(p[name], x/sum(scores), rel_tol=0, abs_tol=2e-6)
               for name, x in zip(option_names, scores, strict=True))
    assert result['native_result']['usage'] == {'input_tokens': len(ids), 'output_tokens': 0, 'sequences': 1}
    assert result['choice'] == row['decision'] == answer[question]['choice'] == max(p, key=p.__getitem__) and row['p_yes'] == p['YES']
    assert result['native_seconds_with_trace'] == row['native_seconds'] <= row['roundtrip_seconds']
    return {**row, 'proof': result['forward_sha256'], 'truth': current['truth'],
            'peak_allocated_bytes': result['peak_allocated_bytes'], 'input_tokens': result['native_result']['usage']['input_tokens']}


def ids_sha(ids):
    return hash_bytes(struct.pack(f'<{len(ids)}q', *ids))


def verify_main(root, template, case, rows, terminal, frames, old_id, action, model, lease):
    requested, finished = event(rows, 'main_request_started'), event(rows, 'actual_main_inference')
    delivery, result = terminal['delivery'], terminal['main_result']
    if not delivery:
        assert not any((requested, finished, result)) and terminal['status'] != 'main_inference_completed'
        return None, None
    assert only(requested) == delivery and terminal['status'] == 'main_inference_completed'
    d = root / 'run' / 'primary' / delivery['request_id']
    verify_admission(d, model, lease, 'primary')
    assert result == load(d / 'result.json') and result['reply_sha256'] == sha(d / 'native-generation.json')
    response, wire = load(d / 'native-generation.json'), load(d / 'wire.json')
    assert wire['request_id'] == result['request_id'] == delivery['request_id']
    old, current = frames[old_id], frames[delivery['capture_id']]
    assert delivery['previous_capture_id'] == old_id and delivery['no_extra_auxiliary_text'] is True
    assert wire['images'] == result['ordered_images'] == [old['candidate_sha'], current['candidate_sha']]
    assert delivery['previous_sha256'] == old['candidate_sha'] and result['current_image_sha256'] == delivery['image_sha256'] == current['candidate_sha']
    assert only(finished) == {'request_id': delivery['request_id'], 'capture_id': delivery['capture_id'],
                              'image_sha256': current['candidate_sha'], 'reply_sha256': result['reply_sha256'],
                              'native_forward_count': result['forward_count'], 'eos': result['natural_eos']}
    body = wire['body']
    assert result['wire_sha256'] == sha(d / 'wire.json') and result['body_sha256'] == delivery['body_sha256'] == hash_bytes(canonical(body))
    assert {k: v for k, v in body.items() if k != 'messages'} == {k: v for k, v in template.items() if k != 'messages'}
    sysmsg, pre, act, post = body['messages']
    assert [sysmsg] == template['messages'] and (pre['role'], act['role'], post['role']) == ('user', 'assistant', 'user')
    assert act['content'] == '<action>' + canonical(action['native_action']).decode() + '</action>'
    original_text, previous_image = pre['content']
    current_image = only(post['content'])
    assert original_text == {'type': 'text', 'text': 'Task: ' + case['task']}
    for block, frame in ((previous_image, old), (current_image, current)):
        assert block['type'] == 'image_url' and unurl(block['image_url']['url']) == Path(frame['candidate_png']).read_bytes()
    assert result['messages_sha256'] == response['request_messages_sha256'] == hash_bytes(canonical(body['messages']))
    assert result['first_forward'] == load(d / 'first-forward.json') == load(d / 'expected-inputs.json')
    assert {'pixel_values', 'image_grid_thw', 'input_ids'} <= result['first_forward'].keys()
    assert ids_sha(response['input_ids']) == result['first_forward']['input_ids']['sha256']
    gen = response['generation_config']
    assert gen['max_new_tokens'] == body['max_tokens'] == 2048 and gen['do_sample'] is False
    eos = gen['eos_token_id']
    result_ids = response['generated_ids']
    assert result['forward_count'] > 0 and result_ids
    assert result['output_tokens'] == len(result_ids) and result['input_tokens'] == len(response['input_ids'])
    assert result['natural_eos'] == (result_ids[-1] in ([eos] if isinstance(eos, int) else eos) and not response['hit_output_cap'])
    assert result['text'] == response['text'] and response['environment_actions_executed'] == 0
    return result, current


def verify_gate(case, rows, frames, flash, action, old, terminal):
    per_frame = {}
    for row in flash:
        per_frame.setdefault(row['capture_id'], []).append(row)
    boundary_ids = set()
    for b in event(rows, 'trusted_static_boundary'):
        assert b['capture_id'] not in boundary_ids and case['arm'] == 'boundary'
        assert b['not_a_flash_yes'] is True and frames[b['capture_id']]['truth'] == 'boundary'
        boundary_ids.add(b['capture_id'])
    holds = event(rows, 'withhold_and_recapture')
    by_hold = {h['capture_id']: h for h in holds}
    assert holds == terminal['holds'] and len(holds) == len(by_hold)
    accepted = {a['capture_id']: a for a in event(rows, 'gate_accepted')}
    windows = {row['stage']: row for row in event(rows, 'study_window_started')}
    assert len(windows) == (2 if action else 1)
    for stage, win in windows.items():
        assert win['end_ns']-win['start_ns'] == 18 * 10**9
        if stage == 'post_action':
            assert win['start_ns'] == action['send_end_ns']
    for stop in event(rows, 'study_window_closed'):
        assert stop['fail_open'] is False and stop['end_ns'] == windows[stop['stage']]['end_ns']
        assert stop['closed_ns'] >= stop['end_ns'] or stop['status'] == 'operator_stopped'
    for cap, frame in frames.items():
        stage = 'post_action' if frame['action_sequence'] else 'initial'
        calls = per_frame.get(cap, [])
        stages = [c['kind'] for c in calls]
        temporal = case['temporal'] and frame['action_sequence'] and cap not in boundary_ids
        assert stages in ([[], ['temporal'], ['temporal', 'quality']] if temporal else [[], ['quality']])
        assert not calls or frame['presence'] == frame['receipt'] == 'YES'
        if len(calls) == 2:
            assert calls[0]['decision'] == 'YES'
        if cap in by_hold:
            hold = by_hold[cap]
            assert hold['stage'] == stage and hold['sha256'] == frame['candidate_sha']
            assert hold['action_repeated'] is False and hold['sleep_seconds'] == .5 and cap not in accepted
            if frame['presence'] == 'NO':
                assert hold['reason'] == 'image_presence_NO'
            elif frame['receipt'] == 'NO':
                assert hold['reason'] == 'receipt_NO'
            else:
                assert calls[-1]['decision'] == 'NO'
                assert hold['reason'] == {'quality': 'single_image_quality_NO', 'temporal': 'temporal_pending_or_unsupported'}[calls[-1]['kind']]
        if cap in accepted:
            win = windows[stage]
            accept = accepted[cap]
            assert accept['stage'] == stage and accept['window_end_ns'] == win['end_ns']
            assert frame['finished_ns'] <= calls[-1]['finished_ns'] <= accept['accepted_ns'] < win['end_ns']
            assert calls[-1]['decision'] == 'YES' and calls[-1]['kind'] == 'quality'
            assert accept['quality_request_id'] == calls[-1]['request_id']
    ordered = list(frames.values())
    for previous, current in zip(ordered, ordered[1:]):
        cid = previous['capture_id']
        if cid in by_hold:
            latest = per_frame[cid][-1]['finished_ns'] if cid in per_frame else previous['finished_ns']
            assert previous['action_sequence'] == current['action_sequence']
            assert current['started_ns'] - latest >= 500 * 10**6
    if old:
        assert accepted[old]['stage'] == 'initial'
    if terminal['delivery']:
        d = terminal['delivery']
        a = accepted[d['capture_id']]
        assert a['stage'] == 'post_action' and a['accepted_ns'] == d['gate_accepted_ns']
        assert a['quality_request_id'] == d['last_quality_request_id']
    assert terminal['calls'] == {'quality': sum(f['kind'] == 'quality' for f in flash),
                                 'temporal': sum(f['kind'] == 'temporal' for f in flash),
                                 'primary': int(terminal['delivery'] is not None)}
    return by_hold, boundary_ids


def timing(values):
    if not values:
        return None
    return {'n': len(values), 'median_s': round(median(values), 3),
            'p90_s': round(quantiles(values, n=10, method='inclusive')[8] if len(values) > 1 else values[0], 3),
            'max_s': round(max(values), 3)}


def metrics(panel):
    return {
        'planned': len(panel), 'settled': sum(row['status'] not in ('technical_incomplete', 'unattempted') for row in panel),
        'post_action_attempted': sum(bool(row.get('action')) for row in panel),
        'first_fault_seen': sum(row.get('first_truth') in FAULT for row in panel),
        'first_fault_held': sum(row.get('first_fault_held', False) for row in panel),
        'effective_recovery': sum(row.get('effective_recovery', False) for row in panel),
        'fault_delivered': sum(row.get('delivery_truth') in FAULT for row in panel),
        'ambiguous_delivered': sum(row.get('delivery_truth') == 'ambiguous' for row in panel),
        'ready_delivered': sum(row.get('delivery_truth') in READY for row in panel),
        'initial_first_false_hold': sum(row.get('initial_first_false_hold', False) for row in panel),
        'initial_no_action': sum(row['status'] == 'initial_observation_window_ended' for row in panel),
        'post_window_censored': sum(row['status'] == 'post_action_observation_window_ended' for row in panel),
        'first_ready_seen': sum(row.get('first_truth') in READY for row in panel),
        'first_ready_false_hold': sum(row.get('first_ready_false_hold', False) for row in panel),
        'any_post_ready_false_hold': sum(row.get('any_post_ready_false_hold', False) for row in panel),
        'ready_uninterrupted': sum(row.get('ready_uninterrupted', False) for row in panel),
        'actual_main_results': sum(bool(row.get('main')) for row in panel),
        'main_natural_EOS': sum(bool(row.get('main') and row['main']['natural_eos']) for row in panel),
        'post_gate_time': timing([row['post_gate_seconds'] for row in panel if row.get('post_gate_seconds') is not None]),
        'ready_gate_time': timing([row['post_gate_seconds'] for row in panel if row.get('delivery_truth') in READY]),
    }


def judge(root):
    root = root.resolve()
    run = root / 'run'
    seal = load(root / 'local-seal.json')
    assert all(sha(root / name) == digest for name, digest in seal.items())
    input_manifest = load(root / 'manifest.json')
    assert input_manifest['mode'] == 'live' and input_manifest['max_primary_calls'] == 96 and input_manifest['retries_of_model_or_action'] == 0
    assert all(seal[n] == h for n, h in input_manifest['files'].items())
    remote = load(root / 'remote-seal.json')
    assert remote['input_manifest_sha256'] == sha(root / 'manifest.json')
    assert {n: h for n, h in seal.items() if n.startswith('run/')} == remote['files']
    plan, template = load(root / 'live_plan.json'), load(root / 'actor-template.json')
    assert plan['max_primary_calls'] == len(plan['cases']) == 96
    top = load(run / 'terminal.json')
    assert top['planned_episodes'] == 96 and top['official_score_calls'] == top['paid_API_calls'] == top['old_queues_launched'] == 0
    finished = {s['case']['id']: s for s in top['sessions']}
    assert list(finished) == [c['id'] for c in plan['cases'][:len(finished)]]
    if top['status'] == 'completed_panel':
        assert len(finished) == 96 and not top['error'] and remote['exit_status'] == 0
    sources = run / 'source'
    origin = load(sources / 'source.json') if (sources / 'source.json').is_file() else None
    lease = load(run / 'gpu-lease.json') if (run / 'gpu-lease.json').is_file() else None
    models = {}
    release = load(run / 'gpu-release.json') if (run / 'gpu-release.json').is_file() else None
    if origin:
        assert origin['fixture_sha256'] == sha(root / 'fixture.html') and origin['source_code_sha256'] == sha(root / 'capture_gui.py')
        assert origin['source']['uid'] == origin['browser']['uid'] == 1033
        assert origin['debug_transport'] == 'inherited anonymous pipes (no listener)'
        # Chrome sometimes rewrites /proc cmdline into a single spaced field.
        argv = ' '.join(origin['browser']['cmdline']).split()
        assert '--remote-debugging-pipe' in argv and not any(x.startswith('--remote-debugging-port') for x in argv)
        assert any(x.endswith('/'+root.name+'/browser-profile') and x.startswith('--user-data-dir=') for x in argv)
    if lease:
        assert lease['holder']['uid'] == 1033 and lease['holder']['cmdline'][-1] == 'live_run.py'
        assert lease['roles']['primary']['physical'] == plan['primary_physical_gpus']
        assert lease['roles']['flash']['physical'] == [plan['flash_physical_gpu']]
        assert len(lease['locks']) == 12 and not lease['smi_before']['compute'] and not lease['smi_after']['compute']
        assert min(c['free_mib'] for c in lease['smi_after']['cards'].values()) >= 23000
        for role in ('flash', 'primary'):
            d = run / role / 'loaded.json'
            if d.is_file():
                model = models[role] = load(d)
                argv = model['process']['cmdline']
                assert model['process']['uid'] == 1033 and model['BF16'] is True and argv[-1] == role
                assert argv[-2].endswith('/' + root.name + '/live_models.py')
                assert model['native_sdpa' if role == 'flash' else 'SDPA'] is True
        if 'flash' in models:
            assert models['flash']['revision'] == plan['revision']
        if release:
            assert [x['path'] for x in release['locks']] == [x['path'] for x in lease['locks']]
            assert all(x['inode'] == y['inode'] for x, y in zip(release['locks'], lease['locks'], strict=True))
            assert set(release['closed_worker_pids']) >= {m['process']['pid'] for m in models.values()}
            assert not {a['pid'] for a in release['snapshot']['compute']} & set(release['closed_worker_pids'])
    if top['status'] == 'completed_panel':
        assert release and origin and set(models) == {'flash', 'primary'} and set(top['closed_workers'].values()) == {0}
        assert load(sources / 'exit.json') == {'browser_exit': 0, 'identity': origin['browser']}
    cases, verified_requests, cap_ids, session_ids = [], {'primary': set(), 'flash': set()}, set(), set()
    escape_refs = escape_references(run, plan)
    aggregated = {'quality': 0, 'temporal': 0, 'primary': 0}
    for case in plan['cases']:
        label = case['id']
        folder = run / 'episodes' / label
        if label not in finished:
            partial = folder.is_dir()
            cases.append({'id': label, 'case': case, 'status': 'technical_incomplete' if partial else 'unattempted'})
            continue
        terminal = load(folder / 'terminal.json')
        assert case == terminal['case']
        head, events = chain(folder / 'events.jsonl')
        assert head == terminal['journal_head'] and len(events) == terminal['events'] and sha(folder / 'events.jsonl') == terminal['journal_sha256']
        assert events[-1]['kind'] == 'terminal' and events[-1]['data'] == finished[label] == {
            k: v for k, v in terminal.items() if k not in ('journal_head', 'journal_sha256', 'events')}
        frames, action, old_id = verify_frames(folder, sources / label, case, events, terminal, origin, plan['viewport'],
                                              escape_refs.get(case['family'], ()))
        assert not cap_ids.intersection(frames) and terminal['session'] not in session_ids
        cap_ids.update(frames); session_ids.add(terminal['session'])
        asked, replies = event(events, 'flash_requested'), event(events, 'flash_replied')
        assert replies == terminal['flash']
        flash = [verify_flash(root, got, want, frames, old_id, action, models['flash'], lease)
                 for got, want in zip(replies, asked, strict=True)]
        main, current = verify_main(root, template, case, events, terminal, frames, old_id, action, models['primary'], lease)
        held, boundary = verify_gate(case, events, frames, flash, action, old_id, terminal)
        for d, vals in (('flash', flash), ('primary', [main] if main else [])):
            for val in vals:
                assert val['request_id'] not in verified_requests[d]
                verified_requests[d].add(val['request_id'])
        for key, val in terminal['calls'].items():
            aggregated[key] += val
        accepted = terminal['delivery']
        first_init = next(iter(frames.values()), None)
        post = [x for x in frames.values() if x['action_sequence']]
        first = post[0] if post else None
        first_truth = first['truth'] if first else None
        first_held = bool(first and first['capture_id'] in held)
        true_fault_held = first_truth in FAULT and first_held
        true_delivery = current['truth'] if current else None
        cases.append({
            'id': label, 'case': case, 'status': terminal['status'], 'truth_frames': list(frames.values()),
            'flash': flash, 'holds': [{**h, 'truth': frames[cap]['truth']} for cap, h in held.items()],
            'journal_head': head, 'action': action,
            'first_post_capture': first, 'first_truth': first_truth,
            'first_fault_held': true_fault_held,
            'first_fault_hold_stage': held[first['capture_id']]['reason'] if true_fault_held else None,
            'effective_recovery': bool(true_fault_held and true_delivery == 'ready' and current['capture_id'] != first['capture_id']),
            'initial_first_false_hold': bool(first_init and first_init['capture_id'] in held),
            'first_ready_false_hold': first_truth in READY and first_held,
            'any_post_ready_false_hold': any(frames[cap]['truth'] in READY for cap in held),
            'ready_uninterrupted': bool(current and first_truth in READY and first['capture_id'] == current['capture_id']),
            'delivered': current, 'delivery_truth': true_delivery,
            'post_gate_seconds': (accepted['gate_accepted_ns']-action['send_end_ns'])/1e9 if accepted else None,
            'app_boundary_proof_count': len(boundary), 'main': main,
        })
    assert aggregated == top['completed_sessions_call_counts']
    observed = {role: {'started': {p.parent.name for p in (run / role).glob('*/start.json')},
                        'results': {p.parent.name for p in (run / role).glob('*/result.json')}}
                for role in verified_requests}
    if top['status'] == 'completed_panel':
        assert all(observed[role]['started'] == observed[role]['results'] == verified_requests[role] for role in observed)
    matched = []
    for group in sorted({r['case']['group'] for r in cases if r['case']['arm'] == 'defense'}):
        a, b = (only(r for r in cases if r['case']['group'] == group and r['case']['arm'] == arm) for arm in ('original', 'defense'))
        fa, fb = a.get('first_post_capture'), b.get('first_post_capture')
        matched.append({
            'group': group, 'flow': a['case']['flow'], 'original': a['id'], 'defense': b['id'],
            'both_first_early_confirmed': bool(fa and fb and fa['truth'] == fb['truth'] == 'early'),
            'exact_same_confirmed_early_png': bool(fa and fb and fa['truth'] == fb['truth'] == 'early'
                                                    and fa['candidate_sha'] == fb['candidate_sha']),
            'original_fault_delivery': a.get('delivery_truth') == 'early',
            'defense_fault_delivery': b.get('delivery_truth') == 'early',
            'defense_loop_recovered': b.get('effective_recovery', False),
            'gate_seconds_original': a.get('post_gate_seconds'), 'gate_seconds_defense': b.get('post_gate_seconds'),
        })
    return {
        'attempt': root.as_posix(), 'input_seal_sha256': sha(root / 'local-seal.json'), 'status': top['status'],
        'escape_native_transition_refs': {family: sorted(refs) for family, refs in escape_refs.items()},
        'error': top['error'], 'audited_terminals': len(finished), 'bound_signed_captures': len(cap_ids),
        'main_calls': aggregated['primary'], 'model_calls': aggregated,
        'observed_model_records': {r: {k: len(v) for k, v in rec.items()} for r, rec in observed.items()},
        'model_loads': models, 'resource_release': release, 'top_metrics': metrics(cases),
        'by_arm': {arm: metrics([r for r in cases if r['case']['arm'] == arm]) for arm in plan['cases_by_arm']},
        'old_frame_by_flow': {flow: {arm: metrics([r for r in cases if r['case']['flow'] == flow and r['case']['arm'] == arm])
                                     for arm in ('original', 'defense', 'fast')} for flow in OUTCOMES},
        'pairs': matched, 'episodes': cases,
    }


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('attempt', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    audited = judge(args.attempt)
    save(args.out, audited)
    for key in ('status', 'audited_terminals', 'bound_signed_captures', 'model_calls', 'by_arm'):
        print(key, audited[key])
