"""Finalize the human-approved source-ID condition from its sealed template once."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time


HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'remaining28-source-reference-gui-20261110-40'
CHOICE = 'adopt_exact_candidate_quote_reference_wire'
SCOPE = 'original32_minus_four_immutable_terminals_remaining28'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verified_seal(root, expected):
    assert sha(root / 'seal.json') == expected
    for name, digest in read(root / 'seal.json').items():
        path = root / name
        assert path.resolve().is_relative_to(root.resolve())
        assert sha(path) == digest, name


def main():
    assert not OUT.exists(), 'Inspect the existing execution namespace; never finalize twice'
    authority = read(HERE / 'continuation-template-created.json')
    template_root = Path(authority['root'])
    verified_seal(template_root, authority['seal_sha256'])
    assert sha(template_root / 'receipt.json') == authority['receipt_sha256']
    template = template_root / 'runtime-template'
    assert sha(template / 'manifest.json') == authority['manifest_sha256']
    proposal = HERE / 'reviewable-proposal-1794308244065817800'
    verified_seal(proposal, 'bb42f4e7ec49bfedca6c8fdfc69b4ffde437c90b8537dd6771112cae654fe358')
    assert sha(proposal / 'proposal.json') == '604ef737d07e50a2124325126b776268708488abc6dd8d4241e414a9525109af'
    decision = dict(
        schema='explicit-source-reference-human-condition-decision-v1',
        recorded_unix=time.time(),
        source='explicit_human_reply_to_source_reference_condition_question',
        question_item_id='["request_user_input_async","call_390af8eda87f43068f9d3389647b1cea",0]',
        exact_question='是否将已封存的“来源编号→精确原句”修复用于尚未开始的28条原GUI轨迹？核验器选原句编号，Controller恢复原文后仍运行全部原校验；双臂同版，原4终局不重跑，图像、主历史、单图辅助与每轨预算保留。代价是verify提示/解码条件变化，整句单元不能自由截句或拼句；已封例子增加836个system tokens，未来容量和Mirage改善尚未证明。此前实验协议要求条件改变由你决定。详见上方审查报告。',
        exact_human_answer='采用修复，继续剩余28条（推荐）',
        choice=CHOICE, scope=SCOPE,
        proposal_sha256=sha(proposal / 'proposal.json'),
        template_manifest_sha256=authority['manifest_sha256'],
        tracks=28, excluded_immutable_terminals=4, total_original_tracks=32,
        original_images_full_main_history_single_image_auxiliary_and_budgets_retained=True,
        both_arms_same_approved_source_reference_version=True,
        no_additional_semantic_or_model_conditions_authorized=True,
        efficacy_established=False)
    receipt = HERE / 'human-source-reference-condition-decision.json'
    assert not receipt.exists()
    save(receipt, decision)
    authorization = HERE / ('human-source-reference-authorization-' + str(time.time_ns()))
    authorization.mkdir()
    shutil.copyfile(receipt, authorization / receipt.name)
    save(authorization / 'seal.json', {receipt.name: sha(receipt)})

    OUT.mkdir()
    shutil.copyfile(__file__, OUT / 'finalize_approved_once.py')
    shutil.copyfile(receipt, OUT / receipt.name)
    package = OUT / 'runtime-package'
    package.mkdir()
    manifest = read(template / 'manifest.json')
    for name, digest in manifest['files'].items():
        assert sha(template / name) == digest, name
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template / name, target)
    assert sha(template / 'private.token') == manifest['auth_token_sha256']
    shutil.copyfile(template / 'private.token', package / 'private.token')
    shutil.copyfile(receipt, package / receipt.name)

    admission = read(package / 'admission.json')
    admission.update(admit_new_GUI_development=True, source_condition_decision_received=True,
        source_condition_choice=CHOICE, staging_template_only=False,
        distinct_source_reference_wire_condition_not_yet_approved=False,
        human_decision_receipt_sha256=sha(receipt),
        approved_proposal_sha256=sha(proposal / 'proposal.json'))
    (package / 'admission.json').write_text(json.dumps(admission, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    manifest.update(schema='approved-original32-remaining28-source-reference-v1',
        template_only=False, launch_ready=True, authorized_finite_joint_development=True,
        source_condition_choice=CHOICE, source_condition_decision_received=True,
        human_decision_receipt_sha256=sha(receipt),
        approved_source_proposal_sha256=sha(proposal / 'proposal.json'),
        sealed_template_manifest_sha256=authority['manifest_sha256'],
        finalization_unix=time.time(),
        approval_scope=SCOPE,
        local_finalization_does_not_allocate_or_prove_available_resources=True)
    manifest['files'] = {p.relative_to(package).as_posix(): sha(p)
        for p in sorted(package.rglob('*')) if p.is_file() and p.name != 'private.token'}
    save(package / 'manifest.json', manifest)

    sys.path.insert(0, str(package))
    from source_decision_gate import require_finalized
    assert require_finalized(package / 'gpu_server.py') == decision
    from continuation_manifest import remaining_queue, completed_request_ids
    plan = read(package / 'plan.json')
    queue = remaining_queue(plan)
    assert len(queue) == 28 and len(completed_request_ids()) == 437
    assert queue[0]['run_id'] == 'fullhistory23-T003-stale_replace-noaux'
    for name in read(template / 'manifest.json')['files']:
        if name != 'admission.json':
            assert (package / name).read_bytes() == (template / name).read_bytes(), name
    for path in package.rglob('*.py'):
        compile(path.read_text(encoding='utf8'), str(path), 'exec')
    save(OUT / 'CPU-admission.json', dict(passed=True,
        manifest_sha256=sha(package / 'manifest.json'),
        check='approved receipt accepted, original28/437 exclusions bound, only metadata differs from sealed tested template',
        exact_sealed_release_runtime_auxiliary_history_actions_and_budgets_retained=True,
        previous_completed_CPU_controls_not_reexecuted=True,
        original32_tracks16_pairs8_tasks_retained=True,
        remaining14_pairs_are_new_version_stratum_only=True,
        new_model_GPU_GUI_scorer_paid_calls=0))
    save(OUT / 'finalization.json', dict(time=time.time(),
        package=str(package), manifest_sha256=sha(package / 'manifest.json'),
        authorization=str(authorization), human_decision_receipt_sha256=sha(receipt),
        authorization_seal_sha256=sha(authorization / 'seal.json'),
        sealed_template=authority, new_model_GPU_GUI_scorer_paid_calls=0))
    save(OUT / 'finalization-seal.json', {p.relative_to(OUT).as_posix(): sha(p)
        for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
    print(json.dumps(dict(root=str(OUT), manifest_sha256=sha(package / 'manifest.json'),
        approval_received=True, remaining_tracks=28, old_terminal_tracks_excluded=4,
        completed_request_ids_excluded=437, new_model_GPU_GUI_scorer_paid_calls=0)))


if __name__ == '__main__':
    main()
