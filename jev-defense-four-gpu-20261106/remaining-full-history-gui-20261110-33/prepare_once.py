"""Freeze a linked remaining31 orchestration; never resume the terminal first run."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLDROOT = BASE / 'prefill-scheduled-full-history-gui-20261109-32'
OLD = OLDROOT / 'runtime-package'
PACKAGE = HERE / 'runtime-package'
REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def save(p, value):
    with p.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')


def verify(root, expected):
    assert sha(root / 'seal.json') == expected
    for name, value in read(root / 'seal.json').items():
        assert (root / name).resolve().is_relative_to(root.resolve()) and sha(root / name) == value


def replace_one(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    assert not PACKAGE.exists() and not (HERE / 'preparation.json').exists()
    assert sha(OLD / 'manifest.json') == 'c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    old_manifest = read(OLD / 'manifest.json')
    for name, value in old_manifest['files'].items():
        assert sha(OLD / name) == value, name
    replay_authority = read(OLDROOT / 'actual-budget-terminal-replay-created.json')
    replay = Path(replay_authority['root'])
    verify(replay, replay_authority['seal_sha256'])
    assert sha(replay / 'receipt.json') == replay_authority['receipt_sha256']
    assert read(replay / 'receipt.json')['passed']
    collection_authority = read(OLDROOT / 'logical-terminal-fullhistory23-T000-clean-noaux-collected.json')
    collection = Path(collection_authority['collection'])
    verify(collection, collection_authority['seal_sha256'])
    assert sha(collection / 'receipt.json') == collection_authority['receipt_sha256']
    classification_authority = read(OLDROOT / 'terminal-classification-preparation-created.json')
    classification = Path(classification_authority['root'])
    verify(classification, classification_authority['seal_sha256'])
    PACKAGE.mkdir()
    for name in old_manifest['files']:
        if name == 'admission.json':
            continue
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, target)
    (PACKAGE / 'private.token').write_text(secrets.token_hex(32), encoding='ascii')
    for name, source in [('continuation_manifest.py', HERE / 'continuation_manifest.py'),
                         ('terminal_outcome_classification.py', classification / 'terminal_outcome_classification.py')]:
        shutil.copyfile(source, PACKAGE / name)
    (PACKAGE / 'predecessor').mkdir()
    for name, source in [('original-technical-failure.json', replay / 'original-technical-failure.json'),
                         ('actual-budget-terminal-replay-receipt.json', replay / 'receipt.json'),
                         ('logical-terminal-collection-receipt.json', collection / 'receipt.json')]:
        shutil.copyfile(source, PACKAGE / 'predecessor' / name)
    predecessor = dict(original_manifest_sha256=sha(OLD / 'manifest.json'),
        unchanged_full_plan_sha256=sha(OLD / 'plan.json'),
        original_terminal_sha256=sha(replay / 'original-technical-failure.json'),
        excluded_run_ids=['fullhistory23-T000-clean-noaux'],
        replayed_classification=read(replay / 'replayed-classification.json'),
        source_trajectory_semantic_Mirage=None, original_terminal_never_rewritten_or_rerun=True,
        disallowed_completed_model_request_ids=[row['request_id'] for row in read(collection / 'service-preservation.json')['selected_requests']],
        original_collection_authority=collection_authority, actual_budget_terminal_replay_authority=replay_authority,
        total_original_tracks=32, only_unstarted_tracks=31, current_root_initial_counts=dict(actor=0, judge=0, evidence=0))
    save(PACKAGE / 'predecessor.json', predecessor)
    changes = {}
    original_protocol = (OLD / 'protocol.py').read_text(encoding='utf8')
    before = "        self.queue = copy.deepcopy(plan['queue']); self.index = 0; self.active = None"
    after = "        from continuation_manifest import remaining_queue, completed_request_ids\n        self.queue = remaining_queue(plan); self.index = 0; self.active = None"
    protocol = replace_one(original_protocol, before, after)
    old_counts = "copy.deepcopy(self.carryover['initial_transport_counts']) if self.index == 0 else {'actor':0,'judge':0,'evidence':0}"
    new_counts = "copy.deepcopy(self.carryover['initial_transport_counts']) if item['run_id'] == self.carryover['original_track'] else {'actor':0,'judge':0,'evidence':0}"
    protocol = replace_one(protocol, old_counts, new_counts)
    old_ids = "self.ids = set(carryover['disallowed_prior_request_ids']); self.counts = {}; self.done = []; self.failed = False"
    new_ids = "self.ids = set(carryover['disallowed_prior_request_ids']) | completed_request_ids(); self.counts = {}; self.done = []; self.failed = False"
    protocol = replace_one(protocol, old_ids, new_ids)
    assert protocol.replace(after, before).replace(new_counts, old_counts).replace(new_ids, old_ids) == original_protocol
    (PACKAGE / 'protocol.py').write_text(protocol, encoding='utf8')
    changes['protocol.py'] = ['Original full32 tail only, source-sealed predecessor', 'Initial counters bound to run identity, never subset index0', 'Completed111 request IDs cannot be reused']
    runner = (classification / 'staged-run_independent_gui.py').read_text(encoding='utf8')
    source_runner = (OLD / 'run_independent_gui.py').read_text(encoding='utf8')
    marker = ' if a.only_runs:\n'
    replacement = ' from continuation_manifest import remaining_queue\n queue=remaining_queue(plan)\n if a.only_runs:\n'
    updated_runner = replace_one(runner, marker, replacement)
    assert updated_runner.replace(replacement, marker) == runner
    (PACKAGE / 'run_independent_gui.py').write_text(updated_runner, encoding='utf8')
    changes['run_independent_gui.py'] = ['Prepared exact local140 budget terminal classification', 'Original32 validation retained; execute only source-bound remaining31']
    server = (OLD / 'gpu_server.py').read_text(encoding='utf8')
    assert server.count('19140') == 2
    (PACKAGE / 'gpu_server.py').write_text(server.replace('19140', '19141'), encoding='utf8')
    changes['gpu_server.py'] = ['New once-only transport port19141, generation and request processing unchanged']
    launcher = (OLD / 'launch_gui_service_once.py').read_text(encoding='utf8')
    before_package = "BASE / 'runtime-preparation/" + OLDROOT.name + "'"
    after_package = "BASE / 'runtime-preparation/" + HERE.name + "'"
    updated_launcher = replace_one(launcher, before_package, after_package)
    before_output = "BASE / '" + OLDROOT.name + "'"
    after_output = 'Path(' + repr(OUTPUT) + ')'
    updated_launcher = replace_one(updated_launcher, before_output, after_output)
    assert updated_launcher.replace(after_package, before_package).replace(after_output, before_output) == launcher
    (PACKAGE / 'launch_gui_service_once.py').write_text(updated_launcher, encoding='utf8')
    changes['launch_gui_service_once.py'] = ['New package path and new owned data-volume output, original resource and inherited lock checks retained']
    save(PACKAGE / 'admission.json', dict(admit_new_GUI_development=True, formal_efficacy=False,
        original_environment_admission_reused=True, original_caps_and_strict_Controller_retained=True,
        predecessor=predecessor, zero_initial_counters_for_all_remaining_tracks=True,
        authorization='Existing sustained goal and verified owned4-7; only31 original unstarted tracks, no failed-track retry'))
    for p in PACKAGE.rglob('*.py'):
        compile(p.read_text(encoding='utf8'), str(p), 'exec')
    for name in ['release/defense/core.py', 'release/defense/prompts.py', 'release/image_evidence.py',
                 'release/evidence_observer.py', 'model_runtime.py', 'resident_schedule.py', 'prefill_residency.py',
                 'bounded_auxiliary.py', 'unicode_length_guard.py', 'stateless_boundary.py', 'gui_transport.py',
                 'complete_actor_history.py', 'plan.json', 'actor-template.json', 'fixed-prompt.txt']:
        assert sha(PACKAGE / name) == sha(OLD / name), name
    # Every other frozen original source/file remains identical. The token and
    # admission are transport authorization; neither enters either model.
    whitelist = set(changes) | {'admission.json'}
    for name, digest in old_manifest['files'].items():
        assert name in whitelist or sha(PACKAGE / name) == digest, name
    m = copy.deepcopy(old_manifest)
    m.update(schema='GUI-original32-source-bound-remaining31-after-local-budget-terminal-v1',
        outputs=OUTPUT, GUI_output=GUIROOT + '/batch', model_url='http://192.0.2.11:19141',
        tracks=31, total_original_tracks=32, skipped_completed_terminal_tracks=1,
        original32_manifest_sha256=sha(OLD / 'manifest.json'), predecessor_sha256=sha(PACKAGE / 'predecessor.json'),
        worker_source_sha256=sha(PACKAGE / 'gpu_server.py'),
        auth_token_sha256=sha(PACKAGE / 'private.token'),
        terminal_classification_repair_only=True, initial_transport_counts_for_all_remaining_tracks=dict(actor=0, judge=0, evidence=0),
        previous_goal_turn_classification='progress: original terminal fully preserved, actual classification replay and final native111 audit completed',
        storage_tradeoff='New receipts use owned3090 data volume, no original moved/deleted/compressed. Free capacity is checked before launch, not proof that all31 future variable-length tracks fit.',
        source_condition_tradeoffs=old_manifest['source_condition_tradeoffs'] + ' Terminal bookkeeping now distinguishes source-bound local140 budget exhaustion from transport/contract/scorer failure, granting no extra call, recovery or execution. Original first-track terminal remains immutable and its Mirage endpoint unknown. All31 remaining tracks begin at zero and retain their original order and conditions.')
    m['files'] = {p.relative_to(PACKAGE).as_posix(): sha(p) for p in sorted(PACKAGE.rglob('*'))
                  if p.is_file() and p.name not in ['manifest.json', 'private.token']}
    save(PACKAGE / 'manifest.json', m)
    save(HERE / 'preparation.json', dict(time=time.time(), manifest_sha256=sha(PACKAGE / 'manifest.json'),
        original_manifest_sha256=sha(OLD / 'manifest.json'), changes=changes,
        unchanged_original_full_plan_sha256=sha(PACKAGE / 'plan.json'),
        original_first_track_never_relaunched=True, only_unstarted_original_tracks=31,
        all_model_sources_prompts_inputs_validators_and_budgets_unchanged=True,
        pending_price_budget_recovery_NOT_deployed=True, actual_model_GPU_GUI_scorer_calls=0,
        original_runtime_modified=False, actual_launch_not_yet_performed=True,
        fresh_model_negative_WAIT_controls_not_claimed=True))
    result = subprocess.run([sys.executable, '-B', str(HERE / 'check_fresh_continuation.py')], capture_output=True)
    (HERE / 'CPU-checks.stdout.txt').write_bytes(result.stdout)
    (HERE / 'CPU-checks.stderr.txt').write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError('New linked orchestration CPU admission failed: ' + result.stderr.decode('utf8', errors='replace'))
    receipt = dict(time=time.time(), passed=True, manifest_sha256=sha(PACKAGE / 'manifest.json'),
        source_bound_original32_minus_actual_terminal=True, original_first_track_unknown_not_negative=True,
        new_model_GUI_scorer_calls=0, formal_efficacy=False)
    save(HERE / 'CPU-admission.json', receipt)
    print(json.dumps(dict(receipt, preparation=str(HERE / 'preparation.json'), tracks=31)))


if __name__ == '__main__':
    main()
