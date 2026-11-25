"""Qualify a gated future reserve preparer after the interrupted ancestry.

Does not prepare a reserve campaign, claim a task, acquire a GPU lock, stage a
runtime, or call a model. The original 26 rows must finish before its use.
"""
import ast
import importlib.util
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, save, sha
from join_reviewed_results import verify

BASE = HERE.parent / 'flash-four-mode-scale10-20261116-12'
ORIGINAL = BASE / 'reserve-operational-draft-qualification-1794848625939942500'
TARGET = HERE / 'prepare_reserve_after_current.py'
OLD_QUEUE_ASSERT = "    assert interrupted['unstarted_run_ids'] == [row['run_id'] for row in manifest['remaining_queue']]"
NEW_QUEUE_ASSERT = "    assert interrupted['unstarted_run_ids'] == [row['run_id'] for row in json.loads((package / 'current-unstarted-plan.json').read_bytes())['exact_unstarted_queue']]"


def replace_exact(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def original_function(source, name):
    return ast.dump(next(n for n in ast.parse(source).body
                         if isinstance(n, ast.FunctionDef) and n.name == name))


def main():
    assert not TARGET.exists() and not (HERE / 'future-reserve-preparer-current.json').exists()
    assert not (HERE / 'reserve-child-intent.json').exists()
    assert not (HERE / 'completed-report-current.json').exists(), 'This preparation is a pre-terminal metadata draft only'
    verify(ORIGINAL, 'c9749c19afa7d48021e8483804e1e9a22d875a48f64ad5eeba630aae0a36d399')
    source_path = ORIGINAL / 'prepare_reserve_campaign.py'
    original = source_path.read_text('utf8')
    assert sha(source_path) == sha(HERE / 'prepare_reserve_campaign.py')
    source = replace_exact(original,
        "READER_DRAFT = HERE / 'reserve-reader-metadata-staging-1794841585726283000'",
        "READER_DRAFT = HERE.parent / 'flash-four-mode-scale10-20261116-12/reserve-reader-metadata-staging-1794841585726283000'")
    source = replace_exact(source,
        "JOIN_DRAFT = HERE / 'reserve-join-metadata-staging-1794847763748042900'",
        "JOIN_DRAFT = HERE.parent / 'flash-four-mode-scale10-20261116-12/reserve-join-metadata-staging-1794847763748042900'")
    extra = (
        "    # A reserve has a new queue; bind the inherited interruption to its\n"
        "    # original immutable ancestor plan instead of this child's queue.\n"
        "    prior_assert = " + repr(OLD_QUEUE_ASSERT) + "\n"
        "    ancestor_assert = " + repr(NEW_QUEUE_ASSERT) + "\n"
        "    if prior_assert in guard:\n"
        "        assert guard.count(prior_assert) == 1\n"
        "        assert (oldp / 'current-unstarted-plan.json').exists()\n"
        "        original_unstarted = json.loads((oldp / 'current-unstarted-plan.json').read_bytes())\n"
        "        assert original_unstarted['parent_manifest_sha256'] == '874a87681734dbe6ca65e2e76f7512638860b40897e3b80fad08e9bbcd23122b'\n"
        "        assert len(original_unstarted['exact_unstarted_queue']) == 26\n"
        "        guard = guard.replace(prior_assert, ancestor_assert)\n"
        "    if \"'only_original_unstarted_26': True\" in guard:\n"
        "        assert guard.count(\"'only_original_unstarted_26': True\") == 1\n"
        "        guard = guard.replace(\"'only_original_unstarted_26': True\", \"'original_unstarted_26_ancestor_bound': True\")\n"
    )
    anchor = "    guard = (oldp / 'continuation_guard.py').read_text('utf8')\n"
    source = replace_exact(source, anchor, anchor + extra)
    compile(source, str(TARGET), 'exec')
    # No original pre-terminal refusal, task ordering, ownership proof, claim,
    # raw runtime copy, or manager copy logic changes.
    assert original_function(source, 'load_plan') == original_function(original, 'load_plan')
    original_tree, new_tree = ast.parse(original), ast.parse(source)
    for node in original_tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PARENT_CODE' for t in node.targets):
            old_parent = ast.literal_eval(node.value)
    for node in new_tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PARENT_CODE' for t in node.targets):
            new_parent = ast.literal_eval(node.value)
    assert old_parent == new_parent
    old_main = next(n for n in original_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    new_main = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    before_index = next(i for i,n in enumerate(old_main.body)
                        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='guard'for t in n.targets))
    extra_len = len(ast.parse('def _meta():\n' + extra).body[0].body)
    normalized_body = new_main.body[:before_index+1] + new_main.body[before_index+1+extra_len:]
    assert ast.dump(ast.Module(body=normalized_body,type_ignores=[])) == ast.dump(ast.Module(body=old_main.body,type_ignores=[]))
    root = HERE / ('future-reserve-preparer-qualification-' + str(time.time_ns())); root.mkdir()
    # Write bytes explicitly so a copy cannot silently change source line ends.
    TARGET.write_bytes(source.encode('utf8'))
    (root / 'prepare_reserve_after_current.py').write_bytes(TARGET.read_bytes())
    (root / 'original-prepare_reserve_campaign.py').write_bytes(source_path.read_bytes())
    spec = importlib.util.spec_from_file_location('qualified_future_reserve', TARGET)
    preparer = importlib.util.module_from_spec(spec); spec.loader.exec_module(preparer)
    verify(preparer.READER_DRAFT, '133b3d5dc9ec04f7900fa329c1b7a80b1675eea158147df5acf775534fd5c5e0')
    verify(preparer.JOIN_DRAFT, '055c3e655dd5a920eb88014136bc5ec32f4d3b728af202b4c3ea39f9453e545a')
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('A pre-terminal metadata qualification must never reach SSH')
    preparer.remote = forbidden
    fixture = root / 'incomplete-parent-fixture'; fixture.mkdir()
    save(fixture / 'plan.json', {'completed_campaign_report': {'root': str(HERE / 'not-created-completed-report')}})
    save(fixture / 'seal.json', {'plan.json': sha(fixture / 'plan.json')})
    try:
        preparer.load_plan(fixture)
    except AssertionError as exc:
        assert str(exc) == 'A running campaign cannot prepare a reserve child'
        refusal = str(exc)
    else:
        raise AssertionError('Incomplete current queue was accepted')
    assert not calls and not (HERE / 'reserve-child-intent.json').exists()
    # Exercise only the new ancestor assertion with the actual sealed26 source
    # and actual interruption proof. Future queue sizes may be2..5, never26.
    inherited_guard = (PACKAGE / 'continuation_guard.py').read_text('utf8')
    expected_guard = replace_exact(inherited_guard, OLD_QUEUE_ASSERT, NEW_QUEUE_ASSERT)
    expected_guard = replace_exact(expected_guard, "'only_original_unstarted_26': True", "'original_unstarted_26_ancestor_bound': True")
    statement = ast.parse('def _check():\n' + NEW_QUEUE_ASSERT + '\n').body[0].body[0]
    assertion = compile(ast.fix_missing_locations(ast.Module(body=[statement],type_ignores=[])), 'immutable26-ancestor-assertion', 'exec')
    queue = json.loads((PACKAGE / 'current-unstarted-plan.json').read_bytes())['exact_unstarted_queue']
    proof = json.loads((PACKAGE / 'interrupted-parent-3090.json').read_bytes())['result']
    assert len(queue) == 26 and proof['unstarted_run_ids'] == [r['run_id'] for r in queue]
    cases = []
    for count in [2,3,4,5]:
        manifest = {'remaining_queue': [{'run_id':'future-reserve-only-'+str(i)} for i in range(count)]}
        exec(assertion, {'package':PACKAGE,'json':json,'interrupted':proof,'manifest':manifest})
        cases.append({'reserve_count':count,'original26_ancestor_remains_bound':True})
    # Corruption of a bound ancestor queue still fails, even when the reserve
    # has a legitimate different shape. Do not weaken the source constraint.
    bad_proof = {**proof, 'unstarted_run_ids': proof['unstarted_run_ids'][:-1]}
    try:
        exec(assertion, {'package':PACKAGE,'json':json,'interrupted':bad_proof})
    except AssertionError:
        corrupt_rejected = True
    else:
        raise AssertionError('Truncated ancestry escaped the source assertion')
    compile(expected_guard, 'prospective-ancestor-binding-guard', 'exec')
    (root / 'prospective-guard-source.py').write_bytes(expected_guard.encode('utf8'))
    save(root / 'result.json', {'scope':'gated future reserve path/ancestor metadata compatibility only',
        'original_qualified_preparer_binding':{'root':str(ORIGINAL),'seal_sha256':sha(ORIGINAL/'seal.json')},
        'preparer_path':str(TARGET),'preparer_sha256':sha(TARGET),
        'original_load_plan_AST_identical':True,'remote_parent_proof_source_identical':True,
        'main_AST_identical_after_removing_only_ancestor_metadata_insertion':True,
        'existing_count2_to5_readers_and_joins_reused_no_control_rerun':True,
        'incomplete_actual_parent_refused_before_claim_or_SSH':refusal,
        'actual_immutable26_ancestor_assertion_cases':cases,
        'corrupted_ancestor_rejected':corrupt_rejected,
        'current_staged_manifest_sha256':sha(PACKAGE/'manifest.json'),
        'current_runtime_package_and_auditors_unchanged':True,
        'actual_reserve_plan_or_campaign_created':False,'reserve_task_claimed':False,
        'new_GPU_lease':False,'new_model_GUI_calls':0,
        'cannot_use_until_original26_completed_audited_released_and_reported':True})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
    verify(root)
    save(HERE/'future-reserve-preparer-current.json',{'root':str(root),'seal_sha256':sha(root/'seal.json'),
        'preparer_path':str(TARGET),'preparer_sha256':sha(TARGET),'new_model_GUI_calls':0})
    print(json.dumps({'root':str(root),'preparer_sha256':sha(TARGET),'incomplete_parent_refused':True,
        'reserve_queue_shapes_qualified':[2,3,4,5],'no_reserve_campaign_created':True,
        'current_runtime_package_unchanged':True,'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
