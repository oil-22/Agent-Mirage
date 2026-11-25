"""Read-only independent join of user-visible browser events, receipts, and native forwards."""

import argparse
import base64
from pathlib import Path
import sqlite3

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from live_common import canonical, hash_bytes, load, save, sha


def chain(path):
    import json
    head = '0' * 64
    out = []
    for i, raw in enumerate(path.read_bytes().splitlines()):
        row = json.loads(raw)
        assert row['seq'] == i and row['previous'] == head
        head = row.pop('sha256')
        assert head == hash_bytes(canonical(row))
        out.append({**row, 'sha256': head})
    return head, out


def frames(folder, source, events, authority):
    binding = load(source / 'session.json')
    assert binding == events[0]['data'] and events[0]['kind'] == 'session'
    public = bytes.fromhex(binding['public_key'])
    action = load(source / 'action.json')
    final = load(source / 'finish.json')
    assert final['dispatch_calls'] == action['dispatch_calls'] == 1 and final['loader'] == action['loader'] == binding['loader']
    assert action['environment'] == final['environment_id'] == binding['environment_id']
    assert [e['data'] for e in events if e['kind'] == 'actual_native_action'] == [action]
    assert sum(e['kind'] in ('input', 'wheel') for e in final['final_dom']['events']) == 1
    assert all(e['trusted'] for e in final['final_dom']['events'] if e['kind'] in ('input', 'wheel'))
    with sqlite3.connect((folder / 'challenges.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        ledger = {r[0]: r[1:] for r in db.execute('select challenge, sequence, issued_ns, state, reason, closed_ns from challenges')}
    bound = [row['data'] for row in events if row['kind'] == 'receipt']
    assert len(bound) == len(ledger) == len(authority) == final['capture_count']
    verified = {}
    for r, summary in zip(bound, authority, strict=True):
        receipt = r['receipt']
        i = receipt['capture_index']
        origin = load(source / f'capture-{i:03}.json')
        assert receipt == origin['receipt'] and (origin['target'], origin['loader']) == (binding['target'], binding['loader'])
        assert origin['constituent_source'] == 'Page.captureScreenshot'
        assert receipt['session_id'] == binding['session_id'] and receipt['source_code_sha256'] == binding['source_code_sha256']
        assert receipt['environment_id'] == binding['environment_id'] and receipt['key_id'] == hash_bytes(public)
        ch = receipt['challenge']
        assert r['expected'] == {'challenge': ch, 'environment_id': binding['environment_id'], 'action_sequence': receipt['action_sequence']}
        seq, issued, state, why, closed = ledger[ch]
        assert (seq, state, why, r['decision']['value']) == (receipt['action_sequence'], 'accepted', 'receipt_bound_proceed_to_Flash', 'YES')
        assert issued <= receipt['acquired_at_ns'] <= closed
        Ech = Ed25519PublicKey.from_public_bytes(public)
        Ech.verify(bytes.fromhex(receipt['signature']), canonical({k: v for k, v in receipt.items() if k != 'signature'}))
        img = receipt['image_sha256']
        assert sha(folder / (img + '.png')) == img == summary['sha256'] and summary['capture_id'] == receipt['capture_id'] == r['capture_id']
        before, after = origin['before']['events'], origin['after']['events']
        if seq == 0:
            assert i == 1 and origin['capture_finished_ns'] < action['send_begin_ns']
            read = 'before_action'
        else:
            assert seq == 1 and origin['capture_started_ns'] > action['send_end_ns']
            if final['final_dom']['kind'] == 'boundary':
                read = 'boundary_candidate'
            else:
                assert sum(e['kind'] == 'input' for e in after) == 1
                if all(e['kind'] != 'render_applied' for e in after):
                    read = 'early_before_render'
                    assert origin['after']['now_ms'] < next(e['ms'] for e in final['final_dom']['events'] if e['kind'] == 'render_applied')
                elif any(e['kind'] == 'render_painted' for e in before):
                    read = 'after_visible_render'
                    if final['final_dom']['kind'] == 'type':
                        assert origin['before']['city'] == origin['after']['city'] == action['native_action']['text']
                    else:
                        assert origin['before']['heading'] == origin['after']['heading'] == 'Search results for “bicycle”'
                else:
                    read = 'straddling_render'
        assert read == summary['phase_after_the_fact'] and r['capture_id'] not in verified
        verified[r['capture_id']] = {**summary, 'phase': read, 'rel_capture_ms': (origin['capture_finished_ns']-action['send_end_ns']) / 1e6,
                                    'fixture_snapshot': origin['after']}
    return verified, action, final


def flash_check(root, run, rows, expected_png, actual_action):
    evidence = []
    for row in rows:
        rec = run / 'flash' / row['request_id']
        result = load(rec / 'result.json')
        wire, native = load(rec / 'wire.json'), load(rec / 'native-request.json')
        actual, pre = load(rec / 'actual-forward.json'), load(rec / 'expected-inputs.json')
        assert result['wire_sha256'] == row['wire_sha256'] == sha(rec / 'wire.json')
        assert row['forward_sha256'] == result['forward_sha256'] == sha(rec / 'actual-forward.json')
        assert result['native_request_sha256'] == sha(rec / 'native-request.json')
        assert [x['sha256'] for x in native['images']] == result['ordered_images'] == row['images']
        assert row['images'][-1] == expected_png[row['capture_id']]['sha256']
        assert actual['past_key_values'] is None and actual['use_cache'] is False
        assert actual['tensors_per_forward'] == [pre['tensors']] and len(actual['native_readout']) == 1
        assert len(pre['ordered_pixel_slices']) == len(row['images']) == pre['tensors']['image_grid_thw']['shape'][0]
        assert result['choice'] == row['decision'] and result['probabilities']['YES'] == row['p_yes']
        assert max(result['probabilities'], key=result['probabilities'].__getitem__) == result['choice']
        body = wire['body']
        if result['kind'] == 'quality':
            contract = load(root / 'gate-contract.json')
            assert wire['kind'] == 'quality' and result['quality_contract_sha256'] == sha(root / 'gate-contract.json')
            assert native['state'] == contract['state']
            assert native['questions'] == {'usable': {'type': 'choice', 'instructions': contract['question'], 'criteria': contract['options']}}
            assert set(body) == {'image_png_base64', 'image_sha256', 'request_id'}
            img = base64.b64decode(body['image_png_base64'], validate=True)
            assert hash_bytes(img) == body['image_sha256'] == row['images'][0] and len(row['images']) == 1
        else:
            assert wire['kind'] == 'temporal' and set(body) == {'previous', 'action', 'current'}
            assert body['action'] == actual_action and len(row['images']) == 2
            for k, digest in zip(('previous', 'current'), row['images'], strict=True):
                assert hash_bytes(base64.b64decode(body[k].split(',', 1)[1], validate=True)) == digest
        evidence.append({**row, 'phase': expected_png[row['capture_id']]['phase']})
    return evidence


def judge(root):
    run = root / 'run'
    seal = load(root / 'local-seal.json')
    assert all(sha(root / name) == digest for name, digest in seal.items())
    plan = load(root / 'live_plan.json')
    top = load(run / 'terminal.json')
    assert top['status'] == 'completed_panel' and len(top['sessions']) == 7
    report = []
    request_ids = set()
    for case, session in zip(plan['cases'], top['sessions'], strict=True):
        assert case == session['case']
        label = case['id']
        folder, source = run / 'episodes' / label, run / 'source' / label
        terminal = load(folder / 'terminal.json')
        head, events = chain(folder / 'events.jsonl')
        assert len(events) == terminal['events'] and head == terminal['journal_head'] and sha(folder / 'events.jsonl') == terminal['journal_sha256']
        assert events[-1]['data'] == session == {k: terminal[k] for k in session}
        captured, action, final = frames(folder, source, events, session['frames'])
        flash = flash_check(root, run, session['flash'], captured, action['native_action'])
        assert [x['data'] for x in events if x['kind'] == 'flash_replied'] == session['flash']
        assert [x['data'] for x in events if x['kind'] == 'withhold_and_recapture'] == session['holds']
        assert not any(h['action_repeated'] for h in session['holds'])
        delivery, main = session['delivery'], session['main_result']
        if delivery:
            mid = delivery['request_id']
            assert mid not in request_ids
            request_ids.add(mid)
            assert len([e for e in events if e['kind'] == 'actual_main_inference']) == 1
            d = run / 'primary' / mid
            wire, response = load(d / 'wire.json'), load(d / 'native-generation.json')
            cap = captured[delivery['capture_id']]
            assert main == load(d / 'result.json') and main['reply_sha256'] == sha(d / 'native-generation.json')
            assert load(d / 'first-forward.json') == load(d / 'expected-inputs.json') == main['first_forward']
            assert main['forward_count'] > 0 and len(response['generated_ids']) > 0
            old = next(iter(captured.values()))
            assert wire['images'] == [old['sha256'], cap['sha256']] == main['ordered_images']
            body = wire['body']
            assert body['messages'][0] == load(root / 'actor-template.json')['messages'][0]
            assert [b['type'] for b in body['messages'][-1]['content']] == ['image_url']
            assert body['messages'][-2]['content'] == '<action>' + canonical(action['native_action']).decode() + '</action>'
            assert hash_bytes(canonical(body)) == delivery['body_sha256'] == main['body_sha256']
            actual_png = base64.b64decode(body['messages'][-1]['content'][0]['image_url']['url'].split(',', 1)[1], validate=True)
            assert actual_png == (folder / (cap['sha256'] + '.png')).read_bytes()
            assert cap['sha256'] == delivery['image_sha256'] == main['current_image_sha256']
            assert all(h['capture_id'] != delivery['capture_id'] for h in session['holds'])
            assert flash[-1]['phase'] == cap['phase'] and flash[-1]['decision'] == 'YES' and flash[-1]['kind'] == 'quality'
            accepted_ms = (delivery['gate_accepted_ns']-action['send_end_ns']) / 1e6
        else:
            cap, accepted_ms = None, None
            assert session['status'] == 'operator_stopped' and not any(e['kind'] == 'actual_main_inference' for e in events)
        boundary = [e['data'] for e in events if e['kind'] == 'trusted_static_boundary']
        if boundary:
            assert cap and len(boundary) == 1 and boundary[0]['not_a_flash_yes'] is True and label == 'scroll-boundary-temporal'
            assert not any(row['kind'] == 'temporal' for row in flash)
            st = cap['fixture_snapshot']
            assert st['scroll_top'] > 0 and st['scroll_top'] + st['client_height'] == st['scroll_height']
            assert cap['sha256'] == next(iter(captured.values()))['sha256']
        report.append({'id': label, 'effect_arm': case['temporal'], 'delivery_phase': cap['phase'] if cap else None,
                       'dispatched_action': action['native_action'], 'one_actual_dispatch': True, 'each_receipt_signature_verified': True,
                       'png_names': {x['phase']: x['sha256'] + '.png' for x in captured.values()},
                       'capture_ms_after_dispatch': [c['rel_capture_ms'] for c in captured.values() if c['phase'] != 'before_action'],
                       'gate_accepted_ms_after_dispatch': accepted_ms, 'flash': flash,
                       'holds': [{**h, 'phase': captured[h['capture_id']]['phase']} for h in session['holds']],
                       'app_proven_boundary': bool(boundary),
                       'main': {k: main[k] for k in ('request_id', 'text', 'output_tokens', 'input_tokens', 'natural_eos', 'seconds')} if main else None,
                       'journal_head': head, 'case_status': session['status']})
    trace = {r['id']: r for r in report}
    paired = {}
    for which in ('search', 'type'):
        arm, baseline = trace[which+'-delayed-temporal'], trace[which+'-delayed-original']
        paired[which] = bool(baseline['delivery_phase'] == 'early_before_render' and arm['delivery_phase'] == 'after_visible_render'
                             and set(h['phase'] for h in arm['holds']) == {'early_before_render'}
                             and all(h['reason'] == 'temporal_pending_or_unsupported' for h in arm['holds'])
                             and baseline['png_names']['early_before_render'] == arm['png_names']['early_before_render'])
    fast = {key: not trace[key]['holds'] and trace[key]['delivery_phase'] == 'after_visible_render'
            for key in ('search-fast-temporal', 'type-fast-temporal')}
    bound = trace['scroll-boundary-temporal']
    resource = load(run / 'gpu-release.json')
    assert len(resource['locks']) == 12 and set(top['closed_workers'].values()) == {0}
    outcome = {'live_attempt': root.name, 'paired_recovery': paired, 'fast_normal_control_pass': fast,
               'static_no_change_pass': bound['app_proven_boundary'] and not bound['holds'] and bool(bound['main']),
               'real_main_responses': len(request_ids), 'verified_journal_chains': len(report),
               'all_outputs_with_natural_eos': all(r['main'] and r['main']['natural_eos'] for r in report),
               'resource_release': resource, 'counts': top['completed_sessions_call_counts'], 'rows': report,
               'scope': 'Deterministic local real Chromium fixture; no official task scoring or external attacks.'}
    return outcome


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('attempt', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    result = judge(args.attempt)
    save(args.out, result)
    for key in ('paired_recovery', 'fast_normal_control_pass', 'static_no_change_pass', 'real_main_responses', 'counts'):
        print(key, result[key])
