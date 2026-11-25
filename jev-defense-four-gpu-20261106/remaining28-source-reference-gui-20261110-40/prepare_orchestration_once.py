"""Adapt only deployment bookkeeping to the approved28/four-terminal namespace."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'remaining29-full-history-gui-20261110-37' / 'orchestrate.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    target = HERE / 'orchestrate.py'
    assert not target.exists()
    source = OLD.read_text(encoding='utf8')
    changes = []
    def change(before, after, count=1):
        nonlocal source
        assert source.count(before) == count, before
        source = source.replace(before, after)
        changes.append(dict(before=before, after=after, count=count))
    change('remaining29 deployment; preserve all three old endpoints.',
           'remaining28 source-ID deployment; preserve all four old endpoints.')
    change("OLD_OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33'",
           "OLD_OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/remaining29-full-history-gui-20261110-37'")
    change("OLD_GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33'",
           "OLD_GUIROOT = '/data/researcher/jev-defense-four-gpu-20261106/remaining29-full-history-gui-20261110-37'")
    change("assert m['tracks']==29 and m['total_original_tracks']==32",
           "assert m['tracks']==28 and m['total_original_tracks']==32 and m['skipped_completed_terminal_tracks']==4")
    start, end = source.index('def admitted():'), source.index('\ndef stage():')
    source = source[:start] + '''def admitted():
    proof = json.loads((HERE / 'CPU-admission.json').read_bytes())
    assert proof['passed'] and proof['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    m = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, digest in m['files'].items():
        assert sha(PACKAGE / name) == digest, name
    assert m['tracks'] == 28 and m['total_original_tracks'] == 32 and m['skipped_completed_terminal_tracks'] == 4
    assert m['initial_transport_counts_for_all_remaining_tracks'] == dict(actor=0, judge=0, evidence=0)
    assert sha(PACKAGE / 'private.token') == m['auth_token_sha256']
    name = 'human-source-reference-condition-decision.json'
    assert m['human_decision_receipt_sha256'] == sha(HERE / name) == sha(PACKAGE / name)
    decision = json.loads((HERE / name).read_bytes())
    assert decision['choice'] == 'adopt_exact_candidate_quote_reference_wire'
    assert decision['scope'] == 'original32_minus_four_immutable_terminals_remaining28'
    assert m['authorized_finite_joint_development'] and m['source_condition_decision_received']
    assert m['launch_ready'] and not m['template_only']
    return m

''' + source[end:]
    change("old=base/('prefill-scheduled-full-history-gui-20261109-32'if row['run_id']=='fullhistory23-T000-clean-noaux'else'remaining-full-history-gui-20261110-33')",
           "old=base/('prefill-scheduled-full-history-gui-20261109-32'if row['run_id']=='fullhistory23-T000-clean-noaux'else'remaining29-full-history-gui-20261110-37'if row['run_id']=='fullhistory23-T000-stale_replace-noaux'else'remaining-full-history-gui-20261110-33')")
    change("for dirname in['prefill-scheduled-full-history-gui-20261109-32','remaining-full-history-gui-20261110-33']:",
           "for dirname in['prefill-scheduled-full-history-gui-20261109-32','remaining-full-history-gui-20261110-33','remaining29-full-history-gui-20261110-37']:")
    change("'three_original_GUI_terminal_SHAs_bound':closed", "'four_original_GUI_terminal_SHAs_bound':closed")
    change("if os.getuid()==1015:\n base=root.parent", """if os.getuid()==1033:
 reference=json.loads((root/'primary-reference.json').read_bytes())
 dep=Path(reference['primary_dependency_receipt'])
 assert sha(dep)==reference['primary_dependency_receipt_sha256']
 proof=json.loads(dep.read_bytes());deps=Path(proof['dependency_root'])
 assert deps==Path('/home/researcher/defense-resume-20261102-retry2/deps')
 actual={str(p.relative_to(deps)):sha(p)for p in deps.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
 assert actual==proof['dependency_files']
 assert sha(deps/'lmformatenforcer/integrations/transformers.py')=='223e56d56be3f60d14b270c6db6cfedd19000adefb22f9d3aeaf5925a6035f47'
if os.getuid()==1015:
 base=root.parent""")
    change("assert sha(old/'manifest.json')=='e64fc8e42a144cd1cc426942093a6edaf51204fba13918286c41e51f8d7b15ef'",
           "assert sha(old/'manifest.json')=='368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'")
    change("('192.0.2.11',19142)", "('192.0.2.11',19143)")
    change("destination=commands/'remaining29-full-history-gui-20261110-37.json'",
           "destination=commands/'remaining28-source-reference-gui-20261110-40.json'")
    change("temporary=commands/('.remaining29-'+str(os.getpid())+'.tmp')",
           "temporary=commands/('.remaining28-source-reference-'+str(os.getpid())+'.tmp')")
    change("first_run='fullhistory23-T000-stale_replace-noaux'", "first_run='fullhistory23-T003-stale_replace-noaux'")
    change("'first_run':'fullhistory23-T000-stale_replace-noaux'", "'first_run':'fullhistory23-T003-stale_replace-noaux'")
    for before, after in [('stage-approved-remaining29-once-', 'stage-approved-remaining28-source-reference-once-'),
        ('submit-approved-remaining29-owned-lock-launch-once','submit-approved-remaining28-source-reference-owned-lock-launch-once'),
        ('submit-approved-remaining29-native-GUI-once','submit-approved-remaining28-source-reference-native-GUI-once'),
        ('all29_future_full_history_fit_not_proven','all28_future_full_history_fit_not_proven'),
        ('inspect-same-remaining31-UID-command-nine-locks-sealed-replies','inspect-same-remaining28-UID-command-nine-locks-sealed-replies'),
        ('inspect-same-remaining31-native-GUI-identity-chain-no-checker-text','inspect-same-remaining28-native-GUI-identity-chain-no-checker-text')]:
        change(before, after)
    ast.parse(source)
    with target.open('x', encoding='utf8', newline='\n') as stream:
        stream.write(source)
    with (HERE/'orchestration-preparation.json').open('x', encoding='utf8') as stream:
        json.dump(dict(source=str(OLD), source_sha256=sha(OLD), orchestrator_sha256=sha(target),
            changes=changes, deployment_bookkeeping_only=True, runtime_package_edited=False,
            new_model_GPU_GUI_scorer_paid_calls=0), stream, indent=2)
    print(json.dumps(dict(orchestrator=str(target), sha256=sha(target), runtime_package_edited=False)))


if __name__=='__main__':
    main()
