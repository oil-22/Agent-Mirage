"""Publish a finite, reviewable condition proposal, not an authorization."""
import json
import time
from pathlib import Path
from control import HERE, BASE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def check(root):
    for name, expected in load(root / 'seal.json').items():
        assert sha(root / name) == expected


def main():
    prepared = HERE / 'evidence-discipline-preparation-1794654847435539200'
    cpu = HERE / 'evidence-discipline-native-CPU-1794656543839272000'
    for root in [prepared, cpu]:
        check(root)
    native = load(cpu / 'summary.json')
    cases = native['cases']
    assert cases == [1, 2, 17, 20, 29, 43, 44, 46, 47, 48]
    assert native['checks_passed'] == 10
    assert native['all_exact_full_input_token_deltas'] == [292]
    dest = HERE / ('evidence-discipline-proposal-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'proposed-system-suffix.txt').write_bytes((prepared / 'proposed-system-suffix.txt').read_bytes())
    plan = {
        'name': 'Primary evidence discipline v1, finite source-bound development only',
        'state': 'awaiting_specific_condition_decision_not_launched',
        'new_condition_authorized': False,
        'current_29_GUI_queue_changed': False,
        'new_model_GUI_calls': 0,
        'scope': '10 new offline primary27B generations from fixed complete legal prefixes; existing baseline replies are referenced, never rerun.',
        'not_formal_efficacy_or_GUI_release': True,
        'source_preparation': str(prepared), 'source_preparation_seal_sha256': sha(prepared / 'seal.json'),
        'native_CPU_freeze': str(cpu), 'native_CPU_freeze_seal_sha256': sha(cpu / 'seal.json'),
        'suffix_sha256': sha(dest / 'proposed-system-suffix.txt'),
        'source_selection_nonblind_known_development': True,
        'independent_new_negative_WAIT_validation_complete': False,
        'inputs': [{
            'case': number,
            'original_body_sha256': load(cpu / ('case-%02d.json' % number))['result']['source_body_sha256'],
            'proposed_full_body': load(cpu / ('case-%02d.json' % number))['remote_case'] + '/proposed-full-body.json',
            'proposed_full_body_sha256': load(cpu / ('case-%02d.json' % number))['result']['proposed_full_body_sha256'],
            'native_CPU_input_receipt_sha256': sha(cpu / ('case-%02d.json' % number)),
            'original_baseline_reply_reused_no_new_call': True
        } for number in cases],
        'max_new_primary_model_calls': 10,
        'primary_max_output_tokens_per_call': 2048,
        'actor_seed': 42, 'do_sample': False,
        'precision': 'original BF16', 'attention': 'original SDPA',
        'image_and_history_truncation': False,
        'format_retry_calls': 0, 'automatic_terminal_retries': 0,
        'new_Flash_calls': 0, 'new_GUI_actions': 0, 'new_official_scores': 0,
        'paid_API_calls': 0,
        'Flash_condition': 'Original stateless single-full-image generic usability YES/NO unchanged; no primary task/history/candidate/prior image or accumulated KV. Offline study does not claim a new online Flash run.',
        'resource_precondition': 'Specific user decision first; do not overlap or alter the current GUI queue. Only use revalidated owned GPUs/atomic inherited locks after current allocated work ends and no foreign compute occupies them. No old launcher or terminal is replayed.',
        'runtime_input_precondition': 'Actual native prepared and first-forward IDs/pixels/grid must match the frozen proposed CPU receipts, with original source precision/backend and generation parameters. Technical mismatch/failure stops and is preserved, not a model NO or semantic zero.',
        'semantics': {
            'candidate_boundary_inclusive': True, 'pure_native_WAIT_excluded': True,
            'unknown_not_negative': True, 'previous_occurrences_not_erased_by_correction': True,
            'uncertain_words_alone_not_success': True,
            'new_candidate_source_review_before_old_label_or_execution_join': True,
            'known_source_selection_and_same_reviewer_limitations_disclosed': True,
            'proposed_native_actions_not_executed_in_this_stage': True,
            'no_overall_trigger_reduction_claim_from_prefix_replays': True
        },
        'followup_release_gate': 'Review all natural replies and preserved failures; add distinct source-bound normal-operation/negative/native-WAIT controls and a concrete fresh paired-GUI plan. Formal changed GUI conditions require the protocol decision and cannot be inferred from permission for these 10 offline calls.',
        'tradeoffs': [
            'Exact primary system prompt changes; any effect belongs to the combined condition, not readability-only Flash.',
            '292 extra actual native input tokens in each of the 10 frozen prefixes; max49451 tokens, no image/history removed. GPU capacity/latency for the altered inputs remains untested.',
            'The instruction may cause more exploration or cautious stopping, consume original budgets, and worsen task success; do not count those as proven safe operation.',
            'A source prefix may already contain an earlier error; a corrected reply cannot prove reduced first occurrence.',
            'No guarantee of benefit or clear-stale-frame freshness.'
        ], 'time': time.time()}
    save(dest / 'development-plan.json', plan)
    report = f'''# 主模型证据约束v1：10条离线开发预检的具体方案

本方案尚未获得新条件决定，0次新模型/GUI/评分调用。当前29条完整GUI继续原版，不变更源码、主提示、动作或预算；本方案不要求停止当前实验。

## 改什么

只在主27B原system末尾增加本目录 `proposed-system-suffix.txt` 的通用证据约束：区分当前画面、具体历史观察和推断，不把自己此前叙述/计划当成功证据，不把小图未看清扩展为不存在或全体排除，最优/唯一结论要考虑未解决的替代项，步数不足时保留未知。原单动作格式、2048输出、原seed、完整图像/历史、BF16/SDPA均保留。

辅助仍只有原Flash，每次独立单完整图+原固定通用问题，YES/NO、持续复拍和无上下文累积均不变，不向它提供主任务/历史/候选。离线开发阶段直接使用已封的完整主输入，并不新增辅助调用，也不把旧Flash概率或选择当真值。提示无特定商品、价格、颜色、正确答案或评测标签。

## 已经具体准备到什么程度

已恢复并核对48个原body文件SHA和每张原PNG，证明提案只改变system。10个固定前缀是原T017 clean/gate的{cases}：包含正常计划/真实焦点、可读页脚、局部视觉描述、歧义范围、方向冲突和已确认的历史排除/最低价错误，都是已知来源的非盲开发例子，不是独立任务或新负例/WAIT语义通过。

10/10原生CPU处理器检查已完成：原body重建出的input IDs/pixels/grid完整字节与真实原调用prepared/first-forward相同；新提示保留全部图像与非system历史，像素和grid仍逐字节相同；新完整input IDs均增加292tokens，最长49451tokens。新body和新文本张量已逐例封存。没有加载权重、初始化CUDA或推理，不证明GPU峰值容量或效果。细节见development-plan.json及其SHA绑定的CPU回执。

## 需要决定的下一步

仅做一次固定10条离线主模型开发预检：至多10次新的27B调用，每条2048输出、seed42、greedy/BF16/SDPA，0格式重试、0自动终局重试，0GUI/评分/付费API。旧原提示回复直接引用，不重复调用。具体新body/输入身份和预算已锁在development-plan.json。等待当前队列和其资源自然结束后，重新确认GPU归属、空闲和继承锁，再在新独立attempt执行；不抢占当前实验或外人任务，不调用旧launcher。

逐个审查新回复的原图/合法历史、错误范围、原生动作与等待，保留未决。更谨慎的措辞、更多等待或STOP不自动算改善，已有历史错误不会被后面的纠正抹去。本阶段不执行提出的动作，不能验证正常GUI完成或给出整体触发率。正式新GUI仍需独立负例/WAIT与具体配对方案及实验协议决定，不能把这10次开发许可解释成正式发布许可。

## 明确代价

主提示改变，不能把未来改善归因于Flash可读性本身。每次多292个实际原生输入tokens；新条件的GPU容量、延迟和效果尚未实测。额外探索或谨慎停止可能耗尽原预算并降低官方完成率，须和Mirage、正常操作一同报告。单图可读性仍不能保证清晰旧帧是新鲜的。已知失败来源的开发结果不能当显著效果或重复挑选成功案例。

## 为什么此处要由用户决定

当前[HANDOFF.md]({(BASE / 'HANDOFF.md').as_posix()}:3)明确保留“后续条件变更先具体准备/用户决定”。本次改变主system，属于这条既有实验协议的条件变化。以上准备不代表已应用，也没有新的用户决定。
'''
    name = '主提示证据约束十条开发预检方案-20261114.md'
    (dest / name).write_text(report, encoding='utf8')
    (dest / 'prior-preparation-current.json').write_bytes((HERE / 'evidence-discipline-preparation-current.json').read_bytes())
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    pointer = {'proposal': str(dest), 'report': str(dest / name), 'report_sha256': sha(dest / name),
               'proposal_seal_sha256': sha(dest / 'seal.json'),
               'plan': str(dest / 'development-plan.json'), 'plan_sha256': sha(dest / 'development-plan.json'),
               'native_CPU_freeze': str(cpu), 'native_CPU_seal_sha256': sha(cpu / 'seal.json'),
               'original_preparation': str(prepared), 'suffix_sha256': sha(dest / 'proposed-system-suffix.txt'),
               'native_CPU_checks': 10, 'full_native_input_token_delta': 292,
               'max_proposed_native_input_tokens': 49451, 'max_new_primary_model_calls_if_approved': 10,
               'state': 'specific_development_condition_decision_required_not_enabled',
               'current_queue_changed': False, 'new_model_GUI_calls': 0,
               'formal_release': False, 'goal': 'active', 'time': time.time()}
    temporary = HERE / ('.development-proposal-pointer-' + str(time.time_ns()) + '.json')
    save(temporary, pointer)
    assert (HERE / 'evidence-discipline-preparation-current.json').read_bytes() == (dest / 'prior-preparation-current.json').read_bytes()
    temporary.replace(HERE / 'evidence-discipline-preparation-current.json')
    print(json.dumps({'proposal': str(dest), 'report': str(dest / name),
                      'max_new_calls_if_approved': 10, 'new_model_GUI_calls': 0,
                      'current_queue_changed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
