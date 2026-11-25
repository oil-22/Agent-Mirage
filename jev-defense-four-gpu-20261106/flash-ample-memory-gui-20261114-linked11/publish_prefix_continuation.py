"""Publish a checked continuation receipt without changing an experiment."""
import argparse
import json
import time
from pathlib import Path

from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verified(root):
    root = root.resolve()
    assert root.parent == HERE
    seal = load(root / 'seal.json')
    assert seal and all(sha(root / name) == h for name, h in seal.items())
    return root


def main():
    p = argparse.ArgumentParser()
    for name in ('native', 'review', 'binding', 'progress'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--metadata-addendum', type=Path)
    p.add_argument('--offline-export-preparation', type=Path)
    a = p.parse_args()
    native, review, binding = [verified(v) for v in (a.native, a.review, a.binding)]
    progress = a.progress.resolve()
    assert progress.parent == HERE
    summary, source, joined, actual = [load(v) for v in (
        native / 'summary.json', review / 'review.json',
        binding / 'binding.json', progress)]
    assert source['partial_prefix_only'] and not source['completed_trajectory_review']
    assert source['unreviewed_within_exported_prefix'] == 0
    assert actual['3090']['result']['terminal'] is None
    assert all(v['same_live_process'] for v in actual['3090']['result']['actual_processes'].values())
    assert not (HERE / 'evidence-discipline-offline-preparation-01/submission.json').exists()
    # The complete native/controller reader records paths as well as their seals.
    assert joined['source_review'] == str(review) and joined['native_audit'] == str(native)
    assert joined['source_review_seal_sha256'] == sha(review / 'seal.json')
    assert joined['native_audit_seal_sha256'] == sha(native / 'seal.json')
    addendum = verified(a.metadata_addendum) if a.metadata_addendum else None
    prepared = verified(a.offline_export_preparation) if a.offline_export_preparation else None
    if prepared:
        preparation = load(prepared / 'preparation.json')
        assert preparation['reader_compiled_only'] and not preparation['actual_export_executed']
    stage = actual['4090']['result']['batch_status']
    count = source['candidate_coverage']
    dest = HERE / ('source-prefix-continuation-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'receipt.json', {
        'time': time.time(), 'native_audit': str(native),
        'native_audit_seal_sha256': sha(native / 'seal.json'),
        'new_raw_main_replies_in_latest_increment': summary['new_raw_main_replies_verified'],
        'cumulative_main_raw_verifications_at_recorded_times': summary['cumulative_verified_main_replies'],
        'cumulative_Flash_raw_verifications_at_recorded_times': summary['cumulative_verified_Flash_replies'],
        'old_raw_not_freshly_rehashed': True, 'fresh_full_postexit_audit_remains_required': True,
        'native_process_and_inherited_locks': summary['actual_processes'],
        'storage_free_bytes_at_audit': summary['storage_free_bytes'],
        'source_review': str(review), 'source_review_seal_sha256': sha(review / 'seal.json'),
        'partial_candidate_coverage': count,
        'definite_positive_candidates': source['definite_positive_candidates'],
        'unresolved_candidates': source['unresolved_candidates'],
        'true_first_trigger_not_established_when_earlier_claims_unresolved': True,
        'partial_review_not_a_completed_paired_effect': True,
        'source_native_binding': str(binding), 'binding_seal_sha256': sha(binding / 'seal.json'),
        'descriptive_metadata_addendum': str(addendum) if addendum else None,
        'addendum_seal_sha256': sha(addendum / 'seal.json') if addendum else None,
        'offline_source_export_preparation': str(prepared) if prepared else None,
        'offline_source_export_preparation_seal_sha256': sha(prepared / 'seal.json') if prepared else None,
        'offline_source_export_actually_executed': False,
        'progress': str(progress), 'progress_sha256': sha(progress), 'GUI_snapshot': stage,
        'offline10_submitted': False, 'formal_changed_GUI_authorized': False,
        'runtime_queue_and_frozen_sources_not_edited': True,
        'new_model_GUI_calls_by_this_publisher': 0, 'effectiveness_proven': False,
        'Mirage_reduction': None, 'goal': 'active'})
    old = dest / 'previous-heads'
    old.mkdir()
    heads = (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md')
    for target in heads:
        (old / target.name).write_bytes(target.read_bytes())
    current = HERE / 'continuation-current.json'
    if current.exists():
        (dest / 'previous-continuation-current.json').write_bytes(current.read_bytes())
    save(dest / 'seal.json', {str(f.relative_to(dest)): sha(f) for f in dest.rglob('*') if f.is_file()})
    head = (
        f'## Latest continuation: {stage["completed"]}/29 sealed; source prefix {count} checked\n\n'
        f'Authority: flash-ample-memory-gui-20261114-linked11/{dest.name}/receipt.json. '
        f'Native audit {native.name} adds {summary["new_raw_main_replies_verified"]} new main raw checks; '
        f'cumulative {summary["cumulative_verified_main_replies"]} main / '
        f'{summary["cumulative_verified_Flash_replies"]} Flash. Actual UID/full command/start/UUID/compute '
        'and inherited locks checked. Old raw checks retain original verification times; final fresh '
        'full postexit native/controller audits remain required. No new Flash CPU audit without new replies.\n\n'
        f'Source-only {review.name}: {count} candidates within this exported prefix reviewed, '
        f'definite positives {source["definite_positive_candidates"]}, unresolved '
        f'{source["unresolved_candidates"]}; full original PNGs and exact full legal-history extensions '
        f'checked. {binding.name} binds actual full native inputs, replies, original parser and action payloads. '
        'Partial source labels are not a completed paired effect or an overall rate; earlier unresolved '
        'claims prevent proving the true first trigger. Source labels remain unchanged after the join. '
        'Do not repeat previously reported clean-pair negative results as new discoveries.\n\n'
        + (f'Descriptive metadata only addendum {addendum.name} preserves the original prefix33 review: '
           '7 newly viewed/20 exact-SHA reused/27 total images and 66 user+candidate messages; '
           'the earlier reader inherited descriptive counts from prefix24. Core rows, labels and '
           'bindings unchanged. Reader now prepares accurate extension counts; completed reviews not rerun.\n\n'
           if addendum else '')
        + (f'New source exporter preparation {prepared.name}: export_offline_source_packets.py '
           'only compiled/sealed, no actual export or inference. After actual offline10 completion '
           'and audit_offline_development_postexit.py succeeds, use --audit <that-audit-root> '
           'to export complete legal inputs/PNGs/new replies for source labels before baseline '
           'comparison; failed/unattempted remain separate. No efficacy result from this preparation.\n\n'
           if prepared else '')
        + f'Actual progress {progress.name}: {stage["run_id"]}, step {stage["step"]}; '
        'GUI/main/Flash/launcher identity matches and original queue continues. Approved offline10 '
        'remains UNSUBMITTED. Only after ALL29 normal terminal/seal/chain completion and actual '
        'GUI/main/Flash/launcher exits, use submit_offline_development.py exactly once with fresh '
        'owned resources/inherited locks. Ten fixed2048output calls, system+292native tokens, '
        '0GUI/Flash/scorer/retry; no authorization reask or automatic formal GUI change. '
        'Never rerun old stages/services/queues/holders/capacity/terminals. Goal ACTIVE; efficacy unproved. '
        'Previous heads below are historical.\n\n')
    for target in heads:
        target.write_text(head + target.read_text(encoding='utf8'), encoding='utf8')
    current.write_text(json.dumps({'checkpoint': str(dest),
                                'receipt_sha256': sha(dest / 'receipt.json'),
                                'seal_sha256': sha(dest / 'seal.json')}, indent=2), encoding='utf8')
    print(json.dumps({'checkpoint': str(dest), 'prefix': count, 'GUI_continues': True,
                      'offline10_submitted': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
