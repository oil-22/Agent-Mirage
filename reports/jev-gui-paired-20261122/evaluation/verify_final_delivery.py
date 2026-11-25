"""Require complete, reproducible evidence before publishing the paired result."""

import argparse
import json
import os
from pathlib import Path
import time

from audit_gate_cycles import audit as audit_gate_cycles
from audit_stale_boundary import audit as audit_stale_boundary
from audit_legal_context import audit as audit_legal_context
from audit_mirage_followup import audit as audit_mirage_followup
from audit_mirage_timing import audit as audit_mirage_timing
from audit_native_execution import check_results as check_native_execution
from audit_normal_alignment import audit as audit_normal_alignment
from audit_paired_image_isolation import audit as audit_paired_image_isolation
from audit_recovery_alignment import audit as audit_recovery_alignment
from audit_review_binding import audit as audit_review_binding
from collect import HERE, VERSIONS, latest_nf4_stage, manifest_for, read, save, sha, stages
from link import link_stage, verify
from render_study_conclusion import render as render_study_conclusion
from representative_cases import choose_cases, render as render_cases
from review_cycle import review_pairs
from summarize import CONDITIONS, arm_record, by_condition_pairs, cohort, load_reviews, pair_records


def checked_index(path):
    verify(path)
    return read(path / 'index.json')


def verified_mirage_followup(ledger_path, report_path, path, sealed, labels):
    receipt = checked_index(path)
    members = {k: Path(v['path']) for k, v in receipt['inputs'].items()}
    assert set(members) == {'packet', 'private', 'judgments'}
    for k, p in members.items():
        assert sha(p / 'seal.json') == receipt['inputs'][k]['seal_sha256']
    replay = audit_mirage_followup(ledger_path, report_path, members['private'], members['judgments'])
    assert replay == receipt and receipt['reviewed_slots'] == sealed
    assert receipt['all_confirmed_definite']['definite_replies'] == sum(
        v['semantic_label'] == 'definite' for v in labels.values())
    return receipt


def verified_native_execution(ledger_path, ledger, path, sealed):
    receipt = checked_index(path)
    assert receipt['ledger_seal_sha256'] == sha(ledger_path / 'seal.json')
    operation = Path(receipt['operation'])
    verify(operation)
    assert sha(operation / 'seal.json') == receipt['operation_seal_sha256']
    assert read(operation / 'stdout.bin') == receipt['result']
    counts = check_native_execution(ledger, receipt['result'])
    assert counts == receipt['evidence_counts'] and counts['sealed_slots'] == sealed
    return receipt


def verified_host_releases(runtime):
    for host, uid in (('3090', 1033), ('4090', 1015)):
        source = runtime['hosts'][host]
        operation = Path(source['operation'])
        verify(operation)
        assert sha(operation / 'seal.json') == source['operation_seal']
        assert read(operation / 'stdout.bin') == source['result']
        assert source['result']['actual_UID'] == uid and not source['result']['new_model_GUI_scorer_calls']


def decisive_bindings(rows, audit):
    index = checked_index(audit)
    proven = index['verified_late_forward_by_request']
    expected = {}
    sampled = 0
    for row in rows:
        tape = row['evidence']
        for step in tape['steps']:
            dose = step['known_injected_dose_at_first_forward']
            recovery = step['recapture_at_actual_forward_needs_visual_review']
            if not (dose or recovery):
                continue
            assert dose != recovery and step['actual_first_forward']
            main = step['main']
            if main['tensor_raw_bytes_fully_audited']:
                sampled += 1
                continue
            request_id = step['request']['request_id']
            assert request_id not in expected
            expected[request_id] = {
                'stage': row['stage_id'], 'role': 'altered_delivery' if dose else 'recapture',
                'run': row['slot']['run_id'], 'step': step['step'], 'request_id': request_id,
                'terminal_sha256': tape['terminal_sha256'], 'natural_EOS': main['natural_EOS'],
                'wire_sha256': main['wire_sha256'], 'seal_sha256': main['seal_sha256'],
                'request_directory': main['runtime_request_directory'],
            }
    assert expected == {k: v['input'] for k, v in proven.items()}

    # The latest index is cumulative. Bind its recorded proofs to each original
    # remote read receipt, and allow a later ledger with no new decisive forward.
    by_receipt = {}
    while True:
        for operation in index['operations']:
            path = Path(operation['operation'])
            verify(path)
            assert sha(path / 'seal.json') == operation['seal']
            result = read(path / 'stdout.bin')
            assert result['actual_gpu_model_browser_or_score_calls'] == 0
            for item in result['requests']:
                key = item['request_id']
                assert key not in by_receipt and expected[key]['stage'] == operation['stage']
                assert item['request_seal_sha256'] == expected[key]['seal_sha256']
                assert item['run'] == expected[key]['run'] and item['step'] == expected[key]['step']
                by_receipt[key] = item
        parent = index['previous_audit']
        if not parent:
            break
        path = Path(parent['path'])
        assert sha(path / 'seal.json') == parent['seal']
        index = checked_index(path)
    assert by_receipt == {k: v['actual_forward'] for k, v in proven.items()}
    return {'all_decisive_forwards_byte_verified': len(proven) + sampled,
            'verified_in_collection': sampled, 'verified_in_later_read_receipts': len(proven)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    p.add_argument('protocol_audit', type=Path)
    p.add_argument('late_forward_audit', type=Path)
    p.add_argument('runtime_release_audit', type=Path, nargs='?')
    p.add_argument('--mirage-followup', type=Path)
    p.add_argument('--native-execution', type=Path)
    a = p.parse_args()
    for path in (a.ledger, a.report):
        verify(path)
    led = read(a.ledger / 'private-linked.json')
    report = read(a.report / 'condition-by-version.json')
    ledger_seal = sha(a.ledger / 'seal.json')
    assert report['ledger_seal_sha256'] == ledger_seal
    rows = led['rows']
    _, _, queue = manifest_for('BF16-original')
    assert [r['slot'] for r in rows] == queue and len(rows) == 100
    sealed = sum(r['status'] == 'verified_terminal' and r['evidence'] is not None for r in rows)
    if sealed != 100 or not report['is_final']:
        print(json.dumps({'ready': False, 'sealed_slots': sealed, 'assigned_slots': 100,
                          'reviewed_pixels': report['reviewed_pixels']}))
        return 1

    if a.runtime_release_audit is None:
        p.error('a full delivery requires the read-only audit_runtime_release.py receipt')
    if a.mirage_followup is None:
        p.error('a full delivery requires the sealed audit_mirage_followup.py result for this ledger')
    if a.native_execution is None:
        p.error('a full delivery requires the archived browser/action/score audit for this ledger')
    latest = latest_nf4_stage()
    runtime = checked_index(a.runtime_release_audit)
    assert runtime['ledger_seal_sha256'] == ledger_seal and runtime['stage'] == latest
    _, start, stop = stages()[latest]
    assert runtime['verified_suffix_slots'] == stop - start
    verified_host_releases(runtime)
    verified_exit = runtime['hosts']['3090']['result']
    pointer, manifest, _ = manifest_for(latest)
    archived_resource_stop = None
    if 'closed_parent_release' in pointer:
        bound = pointer['closed_parent_release']
        path = Path(bound['path'])
        assert sha(path/'seal.json') == bound['seal_sha256']
        old = checked_index(path)
        verified_host_releases(old)
        _, old_start, old_end = stages()[pointer['parent_stage']]
        assert old['stage'] == pointer['parent_stage'] and old['phase'] == 'technical_failure'
        assert old['verified_suffix_slots'] == old_end-old_start and old['cutoff_in_original_100'] == old_end == start
        assert old['verified_never_started_in_stage'] == [r['slot']['run_id'] for r in rows[start:stop]]
        root = Path(pointer['runtime'])
        name = 'resource-stop-resume-link.json'
        assert sha(root/name) == manifest['files'][name]
        link = read(root/name)
        assert link['release_reader_seal_sha256'] == bound['seal_sha256']
        assert link['terminal_sha256_by_run'] == {
            row['slot']['run_id']:row['evidence']['terminal_sha256'] for row in rows[old_start:old_end]}
        archived_resource_stop = {**bound, 'stage':old['stage'], 'verified_prior_slots': old['verified_suffix_slots'],
            'reserved_GPU_hours':old['hosts']['3090']['result']['reserved_GPU_hours']}

    review_sources = review_pairs(a.report)
    quality, labels, sources = load_reviews(led, review_sources)
    originals = {f[k] for r in rows for s in r['evidence']['steps'] for f in s['frames']
                 for k in ('captured_sha256', 'delivered_sha256') if f[k] is not None}
    assert set(quality) == originals
    assert report['reviewed_pixels'] == dict.fromkeys(
        ('eligible_distinct_images', 'reviewed_distinct_images'), len(originals))
    eligible = {(r['slot']['run_id'], s['step']) for r in rows for s in r['evidence']['steps']
                if s['main'] and s['main']['natural_EOS']}
    assert set(labels) == eligible and sources == report['review_sources']
    review_bindings = audit_review_binding(led, review_sources, labels)
    assert review_bindings['reviews_bound_to_full_visible_input'] == len(eligible)
    assert review_bindings['distinct_original_PNGs_byte_checked_in_review_packets'] == len(originals)
    followup = verified_mirage_followup(a.ledger, a.report, a.mirage_followup, sealed, labels)

    protocol = checked_index(a.protocol_audit)
    assert protocol['ledger_seal_sha256'] == ledger_seal
    assert (protocol['assigned_slots'], protocol['assigned_pairs'], len(protocol['assigned_tasks'])) == (100, 50, 10)
    protocol_operation = Path(protocol['operation'])
    verify(protocol_operation)
    assert sha(protocol_operation / 'seal.json') == protocol['operation_seal_sha256']
    assert read(protocol_operation / 'stdout.bin') == protocol['actual_loaded_stage_evidence']
    for stage, (_, start, end) in stages().items():
        source = led['collections'][stage]
        collection = Path(source['path'])
        assert sha(collection / 'seal.json') == source['seal_sha256']
        verify(collection)
        reopened, _, live = link_stage(read(collection / (stage + '.json')))
        assert not live and len(reopened) == end - start
        assert protocol['actual_loaded_stage_evidence'][stage]['started_in_frozen_order'] == end - start
        for row in rows[start:end]:
            assert row['stage_id'] == stage and row['evidence'] == reopened[row['slot']['run_id']]

    metrics = [arm_record(r, quality, labels) for r in rows]
    assert metrics == read(a.report / 'trajectory-metrics.json')
    pairs = list(pair_records(metrics))
    assert pairs == read(a.report / 'paired-metrics.json')
    groups = []
    for version in VERSIONS:
        for condition in CONDITIONS:
            def belongs(record):
                return (record['version'], record['condition']) == (version, condition)

            arms = [r for r in metrics if belongs(r)]
            if arms:
                groups.append({'version': version, 'condition': condition,
                               **{a: cohort([r for r in arms if r['arm'] == a]) for a in ('off', 'on')},
                               'paired': by_condition_pairs([r for r in pairs if belongs(r)])})
    assert groups == report['separate_version_condition_results']
    overall = cohort(metrics)
    assert overall == report['overall_counts_only_no_pooled_effect_estimate']
    native_execution = verified_native_execution(a.ledger, led, a.native_execution, sealed)
    native_counts = native_execution['evidence_counts']
    assert native_counts['official_score_receipts'] == overall['officially_scored']
    forwards = decisive_bindings(rows, a.late_forward_audit)
    gate_cycles = audit_gate_cycles(led, metrics, quality, overall)
    stale_boundary = audit_stale_boundary(led, gate_cycles)
    cases = choose_cases(metrics, pairs, gate_cycles)
    assert [c['condition'] for c in cases['paired_examples']] == list(CONDITIONS[1:])
    alignment = audit_recovery_alignment(led, metrics)
    assert len(alignment['recovery_paths']) == overall['independently_normal_image_reached_actor_after_loop']
    normal_alignment = audit_normal_alignment(led, metrics)
    assert len(normal_alignment['normal_pairs']) == len(protocol['assigned_tasks'])
    image_isolation = audit_paired_image_isolation(led, pairs)
    assert image_isolation['assigned_injection_pairs'] == 4 * len(protocol['assigned_tasks'])
    mirage_timing = audit_mirage_timing(metrics, overall)
    legal_context = audit_legal_context(led)
    assert sum(s['sealed_slots'] for s in legal_context['stage_verification'].values()) == sealed
    assert sum(s['natural_EOS'] for s in legal_context['stage_verification'].values()) == len(eligible)

    out = HERE / 'final-verification' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    inputs = {k: {'path': str(v.resolve()), 'seal_sha256': sha(v / 'seal.json')}
              for k, v in vars(a).items()}
    save(out / 'gate-cycles.json', {'ledger_seal_sha256': ledger_seal,
                                  'metrics_seal_sha256': inputs['report']['seal_sha256'], **gate_cycles})
    save(out / 'representative-cases.json', {'ledger_seal_sha256': ledger_seal,
        'report_seal_sha256': inputs['report']['seal_sha256'], 'final': True, **cases})
    (out / '代表轨迹.md').write_text(render_cases(cases, out), encoding='utf-8')
    tables = Path(os.path.relpath(a.report / '配对证据核验进度.md', out)).as_posix()
    (out / '配对实验结论.md').write_text(render_study_conclusion(
        metrics, pairs, groups, overall, normal_alignment, mirage_timing, image_isolation, tables,
        gate_cycles=gate_cycles, followup=followup, native=native_counts, stale_boundary=stale_boundary), encoding='utf-8')
    save(out / 'recovery-alignment.json', {'ledger_seal_sha256': ledger_seal,
                                         'report_seal_sha256': inputs['report']['seal_sha256'], **alignment})
    save(out / 'normal-alignment.json', {'ledger_seal_sha256': ledger_seal,
                                       'report_seal_sha256': inputs['report']['seal_sha256'], **normal_alignment})
    save(out / 'image-isolation.json', {'ledger_seal_sha256': ledger_seal,
                                      'report_seal_sha256': inputs['report']['seal_sha256'], **image_isolation})
    save(out / 'mirage-timing.json', {'ledger_seal_sha256': ledger_seal,
                                     'report_seal_sha256': inputs['report']['seal_sha256'], **mirage_timing})
    save(out / 'mirage-followup.json', followup)
    save(out / 'native-execution.json', native_execution)
    save(out / 'stale-boundary.json', {'ledger_seal_sha256': ledger_seal, **stale_boundary})
    save(out / 'legal-context.json', {'ledger_seal_sha256': ledger_seal, **legal_context})
    save(out / 'index.json', {'ready': True, 'inputs': inputs, 'slots': sealed, 'pairs': 50,
         'officially_scored': overall['officially_scored'], 'unscored': overall['non_scored_terminals'],
         'reviewed_originals': len(originals), 'reviewed_EOS_replies': len(eligible), **forwards,
         'gate_cycle_decisions_checked': gate_cycles['decisions_checked'],
         'gate_cycle_evidence_sha256': sha(out / 'gate-cycles.json'),
         'representative_cases_sha256': sha(out / 'representative-cases.json'),
         'study_conclusion_sha256': sha(out / '配对实验结论.md'),
         'recovery_alignment_sha256': sha(out / 'recovery-alignment.json'),
         'normal_alignment_sha256': sha(out / 'normal-alignment.json'),
         'image_isolation_sha256': sha(out / 'image-isolation.json'),
         'mirage_timing_sha256': sha(out / 'mirage-timing.json'),
         'mirage_followup_sha256': sha(out / 'mirage-followup.json'),
         'native_execution_sha256': sha(out / 'native-execution.json'),
         'stale_boundary_sha256': sha(out / 'stale-boundary.json'),
         'legal_context_sha256': sha(out / 'legal-context.json'),
         'last_stage_reserved_GPUs': verified_exit['GPU_count'],
         'last_stage_reserved_GPU_hours': verified_exit['reserved_GPU_hours'],
         'archived_technical_stop_release': archived_resource_stop,
         'exact_review_binding_audit': review_bindings,
         'final_auditor_model_GUI_scorer_calls': 0})
    save(out / 'seal.json', {k: sha(out / k) for k in ('index.json', 'gate-cycles.json', 'recovery-alignment.json',
        'normal-alignment.json', 'image-isolation.json', 'mirage-timing.json', 'mirage-followup.json', 'native-execution.json', 'stale-boundary.json',
        'legal-context.json', 'representative-cases.json', '代表轨迹.md',
        '配对实验结论.md')})
    print(json.dumps({'verification': str(out), 'seal_sha256': sha(out / 'seal.json')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
