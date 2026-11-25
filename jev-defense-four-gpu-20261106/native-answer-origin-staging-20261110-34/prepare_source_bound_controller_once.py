"""Freeze a proposed Controller and replay sealed replies on CPU. Never deploy."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining-full-history-gui-20261110-33'
PACKAGE = PREVIOUS / 'runtime-package'
sys.path.insert(0, str(PREVIOUS))
import orchestrate as o
from join_source_reviews import verify_seal
from decoded_answer_source import check_with_exact_answer_source


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sealed_pointer(name, content, hash_key):
    a = read(PREVIOUS / name)
    folder = Path(a['root'])
    assert folder.parent == PREVIOUS and verify_seal(folder) == a['seal_sha256']
    assert sha(folder / content) == a[hash_key]
    return a, folder


def normalized(source):
    tree = ast.parse(source)
    class Normalize(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            if node.module == 'decoded_answer_source':
                return None
            return node

        def visit_Assign(self, node):
            if any(isinstance(t, ast.Name) and t.id == 'DEFENSE_VERSION' for t in node.targets):
                node.value = ast.Constant('version-metadata')
            return self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == 'check_with_exact_answer_source':
                return ast.Call(func=ast.Name(id='check_claim_origins', ctx=ast.Load()), args=node.args[:2], keywords=[])
            return self.generic_visit(node)
    return ast.dump(Normalize().visit(tree), include_attributes=False)


def main():
    pointer = HERE / 'preparation-created.json'
    assert not pointer.exists()
    root = HERE / ('source-bound-controller-CPU-' + str(time.time_ns()))
    root.mkdir()
    for name in ['decoded_answer_source.py', 'test_decoded_answer_source.py', Path(__file__).name]:
        (root / name).write_bytes((HERE / name).read_bytes())
    try:
        manifest = read(PACKAGE / 'manifest.json')
        release = root / 'proposed-release'
        for name, expected in manifest['files'].items():
            if not name.startswith('release/'):
                continue
            original = PACKAGE / name
            assert sha(original) == expected
            target = release / name.removeprefix('release/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original.read_bytes())
        original_source = (PACKAGE / 'release/defense/core.py').read_text(encoding='utf8')
        needle = 'origin=check_claim_origins(checked,candidate)'
        assert original_source.count(needle) == 1
        proposed = original_source.replace(needle,
            'origin=check_with_exact_answer_source(checked,candidate,proposal.get("payload") if isinstance(proposal,dict) else None,check_claim_origins)', 1)
        before = 'from claim_origin import EXACT_CLAIM_INSTRUCTIONS,check_claim_origins'
        assert proposed.count(before) == 1
        proposed = proposed.replace(before, before + '\nfrom decoded_answer_source import check_with_exact_answer_source', 1)
        proposed = proposed.replace("DEFENSE_VERSION='evidence-v4.0.11-dev-quote-units-scoped-absence-20261109'",
            "DEFENSE_VERSION='evidence-v4.0.12-STAGED-native-answer-source-20261110'", 1)
        assert proposed != original_source and normalized(proposed) == normalized(original_source)
        (release / 'defense/core.py').write_text(proposed, encoding='utf8')
        (release / 'decoded_answer_source.py').write_bytes((HERE / 'decoded_answer_source.py').read_bytes())
        for path in release.rglob('*.py'):
            compile(path.read_text(encoding='utf8'), str(path), 'exec')
        sys.path.insert(0, str(PACKAGE / 'release'))
        from defense import core
        assert Path(core.__file__).resolve() == (PACKAGE / 'release/defense/core.py').resolve()
        # Extract only the unchanged pure native parser; no browser imports execute.
        parser_source = PACKAGE / 'native-parser-source.py'
        assert sha(parser_source) == manifest['files']['native-parser-source.py']
        parsed = ast.parse(parser_source.read_text(encoding='utf8'))
        node = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
        namespace = dict(json=json, re=re)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<frozen-native-parser-only>', 'exec'), namespace)
        packet = read(PREVIOUS / 'source-first-packets/1794279236770591500/4335535706704d79f7c6/packet.json')
        native = namespace['parse'](packet['candidate'])
        assert native == packet['native_parser_result']['payload']
        source_reviews = []
        rows = []
        for ident, inp, reply in [
            ('0181', 'source31-postcheck181', 'source31-postcheck181'),
            ('0182', 'source31-format182', 'source31-format182'),
        ]:
            input_authority, input_root = sealed_pointer(inp + '-source-created.json', 'receipt.json', 'receipt_sha256')
            review_authority, _ = sealed_pointer(inp + '-input-review-created.json', 'review.json', 'review_sha256')
            reply_authority, reply_root = sealed_pointer(reply + '-reply-created.json', 'receipt.json', 'receipt_sha256')
            payload = read(input_root / 'payload.json')
            public = payload['view']
            view = core.PublicView(public['observation_id'], public['messages'],
                tuple(core.VisibleImage(base64.b64decode(im['raw_base64'], validate=True), im['role']) for im in public['images']),
                public['recent_action'], public['execution_feedback'], public['observed_at'])
            proposal = dict(name='stop', parsed=True, executor_fallback_wait=False, payload=native, coordinate_space='normalized_1000')
            verdict = json.loads((reply_root / (ident + '-raw.txt')).read_bytes())
            checked = core.validate_verdict(copy.deepcopy(verdict), view, payload['candidate'], proposal)
            before_checked = copy.deepcopy(checked)
            original = core.check_claim_origins(checked, payload['candidate'])
            mapped = check_with_exact_answer_source(checked, payload['candidate'], native, core.check_claim_origins)
            assert original['reject'] and not mapped['reject']
            assert len(mapped['decoded_answer_bindings']) == 1 and mapped['decoded_answer_bindings'][0]['claim_index'] == 3
            assert checked == before_checked and mapped['original_verdict'] == checked
            assert checked['action']['status'] == verdict['action']['status'] == 'insufficient'
            assert [c['status'] for c in checked['claims']] == [c['status'] for c in verdict['claims']]
            downstream = {
                'pagination_count': core.pagination_count_reason_check(checked),
                'minimum_reason': core.minimum_reason_check(checked, core.task_text(view)),
                'explicit_image_sources': core.check_explicit_image_sources(checked, view),
                'historical_event_sources': core.check_historical_event_sources(checked, view),
                'plan_sources': core.plan_source_check(checked, view),
            }
            rows.append(dict(request=ident, input_authority=input_authority, input_review_authority=review_authority,
                reply_authority=reply_authority, unchanged_native_verdict_validator_passed=True,
                original_quote_origin=original, proposed_exact_source_origin=mapped,
                downstream_checks_unchanged=downstream, action_still_insufficient=True,
                new_model_GUI_scorer_calls=0))
            source_reviews.append(review_authority)
        # These exercise the unchanged native schema/evidence validator itself.
        negatives = []
        for label, mutate in [
            ('candidate_only_gui_evidence', lambda v: v['claims'][0].update(status='supported', evidence=[dict(source='candidate', span_id='full')])),
            ('nonexistent_image', lambda v: v['claims'][1]['evidence'][0].update(image_index=999)),
            ('box_outside_original', lambda v: v['claims'][1]['evidence'][0].update(box_xyxy=[0, 0, 1001, 1000])),
        ]:
            invalid = copy.deepcopy(verdict)
            mutate(invalid)
            try:
                core.validate_verdict(invalid, view, payload['candidate'], proposal)
            except core.ValidationError as error:
                negatives.append(dict(case=label, rejected=True, error=str(error)))
            else:
                raise AssertionError('Original evidence validator accepted negative ' + label)
        o.save(root / 'replay.json', dict(schema='STAGED-exact-native-answer-source-CPU-v1',
            original_manifest_sha256=sha(PACKAGE / 'manifest.json'), rows=rows,
            full_Controller_AST_equal_except_version_import_and_source_gate=True,
            original_verdict_schema_evidence_and_all_other_checks_unchanged=True,
            unchanged_native_evidence_negative_checks=negatives,
            earlier_21_source_boundary_unit_tests_observed_passed=True,
            unit_test_observation='functions.exec command completed with exit_code 0: Ran 21 tests; OK. No rerun for reporting.',
            synthetic_negative_and_WAIT_checks_are_not_model_semantic_controls=True,
            one_actual_source_two_original_format_attempts_not_two_independent_controls=True,
            images_main_history_prompts_BF16_actions_budgets_and_old_terminals_unchanged=True,
            actual_GPU_or_GUI_integration_not_run=True, formal_new_condition_not_authorized_by_this_preparation=True,
            proposed_only_deployed=False, automatic_allow_or_completion_certified=False,
            new_model_GPU_GUI_scorer_paid_calls=0, efficacy_established=False, goal='active'))
        report = ('旧181/182核验引用的c4逐字等于实际原生STOP answer解码后的句子。新准备仅为该JSON字符串值建立逐字符到原始候选的来源映射；'
            '保留原字节检查器，先匹配原文，只为无法按原字节匹配的精确STOP答案片段使用新来源通道。'
            '不做任意unescape、Unicode/空白规范化、改词、拼句、改价、否定删改或字段猜测。全部重复来源位置保留。\n\n'
            '21个来源边界CPU检查已通过；本次原始同源两次核验重放保留raw/decoded跨度及SHA。原生schema与证据检查仍执行，'
            '3个候选自证/不存在图片/越界引用负例仍拒绝。主动作及原始核验状态均未编辑：两次action仍insufficient，'
            '不是改成STOP放行，也没有模型、GPU、GUI、官方评分或付费调用。合成WAIT/负例只是协议测试，不是新模型语义控制或防御成功。\n\n'
            '仅准备独立Controller副本，AST确认只增加来源映射导入/调用及版本元数据，原完整图、主历史、固定v6辅助、BF16和预算不变。'
            '新通道改变严格来源规则允许的表示形式；正式启用前需对该差异和既有终局/剩余29轨的分析边界作明确决定。'
            '旧失败轨绝不重跑。最低价、单帧12条、后续页逻辑及已发生Mirage没有由此修复。目标ACTIVE。\n')
        (root / 'report.md').write_text(report, encoding='utf8')
        o.save(root / 'receipt.json', dict(passed=True, source_mapping_only=True, staged_Controller_not_deployed=True,
            raw_source_bytes_unchanged=True, new_model_GPU_GUI_scorer_paid_calls=0))
    except BaseException as error:
        o.save(root / 'preparation-observer-failure.json', dict(error=repr(error), original_sources_unchanged=True,
            no_model_GPU_GUI_calls=True))
        o.save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        raise
    o.save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    result = dict(root=str(root), replay_sha256=sha(root / 'replay.json'), seal_sha256=sha(root / 'seal.json'))
    o.save(pointer, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
