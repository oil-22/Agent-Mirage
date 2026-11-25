"""Replay the prepared classifier on the sealed real terminal, without edits."""
import hashlib
import json
from pathlib import Path
import time

from terminal_outcome_classification import classify_run_termination


HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def save(p, value):
    with p.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')


def verify(folder, expected=None):
    if expected is not None:
        assert sha(folder / 'seal.json') == expected
    for name, digest in read(folder / 'seal.json').items():
        assert (folder / name).resolve().is_relative_to(folder.resolve())
        assert sha(folder / name) == digest, name


def main():
    pointer = HERE / 'actual-budget-terminal-replay-created.json'
    assert not pointer.exists(), 'A completed real terminal replay is not repeated'
    authority = read(HERE / 'logical-terminal-fullhistory23-T000-clean-noaux-collected.json')
    collection = Path(authority['collection'])
    verify(collection, authority['seal_sha256'])
    assert sha(collection / 'receipt.json') == authority['receipt_sha256']
    gui = read(collection / 'GUI-preservation.json')
    service = read(collection / 'service-preservation.json')
    terminal = collection / 'selected-originals/technical-failure.json'
    original = read(terminal)
    assert sha(terminal) == gui['terminal_sha256'] == 'f1adf50d1f5f7d06ee8184b4b82833a7b915cf139d4bd77b904e9a50e9287857'
    assert original['blocked_reason'] == 'point_verifier_error:verifier_call_cap'
    assert original['outcome'] == 'blocked' and original['technical_status'] == 'verifier_failure'
    assert original['scoring_status'] == 'complete' and original['scoring_error'] is None
    assert original['official_reward'] == 0.0 and original['semantic_mirage'] is None
    assert service['original_transport_counts_including_carried_technical_expenditure'] == dict(actor=38, judge=140, evidence=0)
    assert (original['actor_calls'], original['verifier_calls'], original['auxiliary_calls']) == (38, 140, 0)
    assert (original['decisions'], original['environment_actions']) == (37, 36)
    preparation = read(HERE / 'terminal-classification-preparation-created.json')
    prepared = Path(preparation['root'])
    verify(prepared, preparation['seal_sha256'])
    assert sha(prepared / 'receipt.json') == preparation['receipt_sha256']
    assert sha(HERE / 'terminal_outcome_classification.py') == sha(prepared / 'terminal_outcome_classification.py')
    package = HERE / 'runtime-package'
    assert sha(package / 'manifest.json') == 'c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    for name, digest in read(package / 'manifest.json')['files'].items():
        assert sha(package / name) == digest, name
    revised = classify_run_termination(original['outcome'], original['blocked_reason'],
        original['scoring_status'], original['verifier_calls'], 140)
    assert revised['local_verifier_budget_exhausted'] is True
    assert revised['technical_status'] == 'no_reported_infrastructure_failure'
    assert revised['new_calls_or_retries_granted'] == 0
    ledger_authority = read(HERE / 'first38-consolidated-source-ledger-created.json')
    ledger_root = Path(ledger_authority['root'])
    verify(ledger_root, ledger_authority['seal_sha256'])
    assert sha(ledger_root / 'ledger.json') == ledger_authority['ledger_sha256']
    assert ledger_authority['original_distinct_candidates'] == 38
    assert ledger_authority['unresolved_original_candidate_ordinals'] == [38]
    audits = [read(read(HERE / 'prefix-audit-created.json')['audit'])]
    for p in sorted(HERE.glob('new-replies-*-audit-created.json')):
        import re
        if re.fullmatch(r'new-replies-\d+-audit-created.json', p.name):
            binding = read(p)
            assert sha(binding['audit']) == binding['audit_sha256']
            audits.append(read(binding['audit']))
    rows = sorted([row for audit in audits for row in audit['requests']], key=lambda row: row['request'])
    assert [row['request'] for row in rows] == [str(n).zfill(4) for n in range(1, 112)]
    assert all(audit['passed'] for audit in audits)
    totals = {key: sum(audit['totals'][key] for audit in audits)
              for key in ['input_tokens', 'output_tokens', 'native_call_timer_seconds']}
    root = HERE / ('actual-budget-terminal-replay-' + str(time.time_ns()))
    root.mkdir()
    for source in [Path(__file__), HERE / 'terminal_outcome_classification.py']:
        (root / source.name).write_bytes(source.read_bytes())
    (root / 'original-technical-failure.json').write_bytes(terminal.read_bytes())
    save(root / 'replayed-classification.json', revised)
    save(root / 'receipt.json', dict(time=time.time(), passed=True,
        previous_goal_turn_classification='progress: real terminal observed and complete original terminal collection finished',
        collection_authority=authority, prepared_classifier_authority=preparation,
        original_terminal_sha256=sha(terminal), original_terminal_and_original_classification_unchanged=True,
        real_local_budget_exception_source_bound=True, classification_replay=revised,
        original_scoring_status=original['scoring_status'], original_official_reward=original['official_reward'],
        original_run_end_status=gui['run_end']['body']['status'], original_transport_counts=service['original_transport_counts_including_carried_technical_expenditure'],
        original_environment_actions=36, original_decisions=37, distinct_source_candidates=38,
        source_candidate_definite_negative_count=37, source_candidate_unknown_ordinals=[38],
        trajectory_semantic_mirage=None, trajectory_semantic_mirage_unknown_retained=True,
        candidate_level_normal_operation_false_rejection_lower_bound=1,
        prior_technical_interruption_and_original_OOM_expenditure_not_erased=True,
        exact_current_root_audited_requests=111, current_root_audited_totals=totals,
        timer_is_summed_native_calls_not_walltime_currency_or_energy=True,
        no_failed_track_rerun_or_additional_budget_authorized=True,
        remaining_original_31_tracks_not_started_by_this_replay=True,
        frozen_runtime_modified=False, new_model_GUI_scorer_paid_calls=0,
        defense_efficacy_or_goal_completion_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    record = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, record)
    assert sha(terminal) == gui['terminal_sha256']
    print(json.dumps(dict(record, classification=revised, totals=totals)))


if __name__ == '__main__':
    main()
