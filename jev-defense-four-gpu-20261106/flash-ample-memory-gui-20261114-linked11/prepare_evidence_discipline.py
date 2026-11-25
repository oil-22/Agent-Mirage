"""Static preparation only: a generic primary-prompt amendment, never installed.

Reconstructs sealed legal review inputs from their original PNGs, verifies the
exact archived body hash, and checks that only the proposed system suffix
differs. This neither calls a model nor evaluates the amended policy.
"""
import base64
import copy
import hashlib
import json
import time
from pathlib import Path

from control import HERE, save, sha

SUFFIX = """Evidence discipline:
Each screenshot establishes only what is visible in that image. Distinguish current visible facts, facts in an identifiable earlier supplied screenshot, and unresolved inferences. Your earlier narration, plans, and issued actions are not independent evidence that an inspection or navigation succeeded.
Before asserting a visual or historical fact, check the supplied image that supports it. Preserve uncertainty about small, occluded, ambiguous, or uninspected attributes. Do not turn 'not clearly seen' into 'absent', or a statement about visible items into a claim about every item or page. A qualified claim still needs evidence for its actual scope.
For cheapest, most expensive, newest, or unique answers, inspect unresolved alternatives that could change the answer using the original allowed actions. If the existing budget cannot resolve them, state the remaining uncertainty instead of claiming a proven optimum or completed exhaustive search. No additional actions, retries, or output budget are granted.
Readable footers, sparse pages, and no-results pages remain observable; they do not prove facts about offscreen content. Keep the described direction and chosen native action consistent. An issued action is an attempt, not confirmation of its visible result. Native waiting remains allowed when appropriate.
Auxiliary image acceptance, when present, means only that the current image is interpretable. It does not certify freshness, factual claims, historical conclusions, action correctness, or task completion. Retain the exact original one-action output format."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def restore(value, root):
    if isinstance(value, list):
        return [restore(v, root) for v in value]
    if isinstance(value, dict):
        if value.get('type') == 'image_url':
            image = (root / value['image_url']['url']).resolve()
            assert image.is_relative_to(root.resolve())
            data = image.read_bytes()
            assert hashlib.sha256(data).hexdigest() == value['original_PNG_sha256']
            assert data.startswith(b'\x89PNG\r\n\x1a\n')
            return {'type': 'image_url', 'image_url': {
                'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}}
        return {k: restore(v, root) for k, v in value.items()}
    return value


def main():
    packets = HERE / 'semantic-packets-1794653537728198200'
    review_pointer = json.loads((HERE / 'semantic-review-current.json').read_bytes())
    review_path = Path(review_pointer['joined_review'])
    assert sha(review_path) == review_pointer['joined_review_sha256']
    joined = json.loads(review_path.read_bytes())
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for name, expected in json.loads((packets / 'seal.json').read_bytes()).items():
        assert sha(packets / name) == expected
    entries = json.loads((packets / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 48
    dest = HERE / ('evidence-discipline-preparation-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'preparation-source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'proposed-system-suffix.txt').write_text(SUFFIX, encoding='utf8')
    proposed_template = copy.deepcopy(template)
    proposed_template['messages'][0]['content'] += '\n\n' + SUFFIX
    save(dest / 'proposed-actor-template.json', proposed_template)
    source_checks = []
    for number, entry in enumerate(entries, 1):
        packet = json.loads((packets / entry['file']).read_bytes())
        assert sha(packets / entry['file']) == entry['sha256']
        original = restore(packet['legal_full_input_review_projection'], packets)
        # The archived wire transport used sorted keys; compare the exact body
        # file representation, not merely a hash-replaced review projection.
        body_bytes = json.dumps(original, sort_keys=True, ensure_ascii=False, indent=2).encode()
        assert hashlib.sha256(body_bytes).hexdigest() == packet['source_body_sha256'], number
        assert original['messages'][0] == template['messages'][0]
        amended = copy.deepcopy(original)
        amended['messages'][0]['content'] += '\n\n' + SUFFIX
        assert amended['messages'][1:] == original['messages'][1:]
        assert {k: v for k, v in amended.items() if k != 'messages'} == {
            k: v for k, v in original.items() if k != 'messages'}
        recovered = copy.deepcopy(amended)
        recovered['messages'][0]['content'] = template['messages'][0]['content']
        assert recovered == original
        source_checks.append({
            'candidate': number, 'packet_sha256': entry['sha256'],
            'original_body_sha256': packet['source_body_sha256'],
            'reconstructed_exact_original_body_verified': True,
            'proposed_body_canonical_sha256': hashlib.sha256(canonical(amended)).hexdigest(),
            'images_and_all_non_system_messages_unchanged': True,
            'original_candidate_text_not_added_to_input': True,
            'semantic_effect_evaluated': False})
    save(dest / 'source-fidelity-checks.json', {
        'source_packets': str(packets), 'source_seal_sha256': sha(packets / 'seal.json'),
        'checks': source_checks, 'count': len(source_checks), 'model_calls': 0,
        'claim': '48 static input-fidelity checks; not 48 semantic passes or new controls.'})
    panel = [1, 2, 17, 20, 29, 43, 44, 46, 47, 48]
    row_by_number = {r['candidate']: r for r in joined['rows']}
    save(dest / 'PRIVATE-development-review-locators.json', {
        'evaluation_only_never_model_input': True,
        'selected_known_sources_nonblind': True, 'independent_new_controls': False,
        'items': [{'candidate': n, 'packet_sha256': entries[n - 1]['sha256'],
                   'source_review': row_by_number[n]} for n in panel],
        'held_out_source_selection_still_required': True,
        'actual_native_WAIT_and_negative_control_review_still_required': True,
        'new_model_or_GUI_calls': 0})
    status = {
        'state': 'static_preparation_only_not_enabled_or_launch_ready',
        'original_experiment_manifest_sha256': sha(HERE / 'package/manifest.json'),
        'original_actor_template_sha256': sha(HERE / 'package/actor-template.json'),
        'proposed_actor_template_sha256': sha(dest / 'proposed-actor-template.json'),
        'Flash_contract_sha256_unchanged': sha(HERE / 'package/flash/gate-contract.json'),
        'suffix_sha256': sha(dest / 'proposed-system-suffix.txt'),
        'source_review_sha256': sha(review_path),
        '48_input_fidelity_checks_passed': len(source_checks),
        'semantic_tests_passed': None, 'Mirage_reduction': None,
        'new_model_GUI_calls': 0, 'current_queue_modified': False,
        'new_queue_or_resources_created': False,
        'exact_added_native_token_count': None,
        'future_required_decision': 'Change the primary system prompt by this exact suffix, keeping one stateless Flash YES/NO model and all images/full histories/native actions/seeds/budgets. Do not apply until the concrete development controls, resource impact and user decision are recorded.',
        'tradeoffs': [
            'The primary prompt changes; improvement would belong to this combined condition, not Flash readability alone.',
            'Additional system tokens repeat at every decision and may increase latency/memory.',
            'Inspection can consume the existing action budget and reduce official task success.',
            'Uncertain wording alone is not success; unsupported scoped claims still count.',
            'This prompt cannot certify clear stale-frame freshness or guarantee prevention.',
            'No post-actor rejection can erase a Mirage already generated.'
        ],
        'required_before_model_use': [
            'Bound native tokenizer added-token accounting and unchanged full-input limits.',
            'Freeze distinct actual negative, normal-footer, plan-versus-success, visible-focus, ambiguity and pure-native-WAIT sources with independent image review.',
            'Prepare a finite source-bound development comparison with original output/seed/format budget, then record the user decision before any altered condition is delivered.',
            'Fresh complete paired GUI comparison after development; predeclare trajectory occurrence, uncertainty, task success, false blocks and cost. Do not select successful reruns or erase old outcomes.'
        ], 'created': time.time()}
    save(dest / 'status.json', status)
    report = """# 单图门控之外的主模型证据约束：待审准备

本目录只准备一项候选改动，尚未用于任何模型或GUI。当前29条队列、冻结源码和所有旧终局不改。没有新推理，也没有证明降低Mirage。

准备的改动是给主模型原system末尾追加 `proposed-system-suffix.txt` 中的通用证据约束。辅助仍只有一个Flash，仍只收当次完整单图与原固定通用问题，只返回YES/NO，不接收主任务、主历史、候选或前图，不累计上下文；持续复拍规则保持。主模型保留完整合法历史与原图。

该后缀要求区分当前画面、具体历史画面和未决推断；不以自己此前叙述或行动计划证明成功，不把小图看不清变成不存在，不把局部观察扩展成全体排除；最优/唯一结论须考虑可能改变答案的未决候选。只用原有动作和预算检查，超预算仍未解决时如实保留不确定性。原生单动作格式、STOP、WAIT、方向、焦点和正常页脚均保留，不加入特定商品、价格、颜色、正确答案或评测标签。

已做的是48份已封合法输入的静态来源检查：恢复每张原始PNG，完整重建原body并核对原文件SHA，只更改system后缀；其余全部历史消息、图像、生成参数字节内容保持。48项是输入一致性检查，不是48个语义通过。10个已知源仅为非盲开发例子的定位，PRIVATE审查与候选原答复不拼入模型输入。尚缺独立新负例/真实WAIT、精确原生token开销和实际模型比较，所以未达到新条件启动标准。

代价是主提示和输入token条件改变，可能增加延迟、显存或额外探索，消耗原有步数并降低任务完成率；不自动加预算。这一组合若改善，不能归功于Flash本身。软化措辞不自动算正确；仍按实际断言范围、正常操作、完整轨迹触发和未决子断言审查。清晰旧帧仍无法仅由单图确认新鲜，后置拦截也不能抹去已产生的错误。

在独立来源、精确开销和有限开发比较方案准备齐全后，再按原实验协议把这项具体条件变化交给用户决定。此前不投放新提示、不启动新队列。
"""
    (dest / '主模型证据约束候选与条件代价-20261114.md').write_text(report, encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'preparation': str(dest), 'input_fidelity_checks': len(source_checks),
                      'changed_live_sources': False, 'new_model_GUI_calls': 0,
                      'semantic_effect_or_efficacy': None}))


if __name__ == '__main__':
    main()
