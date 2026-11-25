"""Publish a reviewable new-condition proposal. Never launches inference."""
import hashlib
import json
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
BASE = PARENT.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def verify_pointer(name):
    value = json.loads((HERE / name).read_bytes())
    root = Path(value['root'])
    assert sha(root / 'seal.json') == value['seal_sha256']
    return root


def objects(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from objects(item)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def main():
    assert not (HERE / 'publication-current.json').exists(), 'Do not republish a sealed preparation'
    frozen = verify_pointer('frozen-sources-current.json')
    proposed = verify_pointer('proposed-inputs-current.json')
    cpu = verify_pointer('native-CPU-current.json')
    failure = verify_pointer('native-CPU-failure-preservation-current.json')
    cpu_summary = json.loads((cpu / 'summary.json').read_bytes())
    assert cpu_summary['cases'] == 10 and cpu_summary['new_model_GUI_Flash_scorer_calls'] == 0
    assert cpu_summary['all_new_visual_tensors_equal_prior_actual_source_forward']
    checks = json.loads((proposed / 'CPU-boundary-checks.json').read_bytes())
    assert checks['failed'] == 0 and checks['passed'] == 57
    rows = json.loads((frozen / 'PRIVATE-source-index.json').read_bytes())
    registry_root = PARENT / 'semantic-coverage-registry-1794681968796492900'
    registry_seal = json.loads((registry_root / 'seal.json').read_bytes())
    assert sha(registry_root / 'registry.json') == registry_seal['registry.json']
    registry = json.loads((registry_root / 'registry.json').read_bytes())
    private = []
    for row in rows:
        label = next(r for r in registry['rows'] if r['request_id'] == row['request_id'])
        assert label['request_seal_sha256'] == row['seal_sha256']
        assert label['candidate'] == row['decision'] and label['image_sha256'] == row['current_image_sha256']
        publication = Path(label['publication'])
        assert sha(publication / 'seal.json') == label['publication_seal_sha256']
        seal = json.loads((publication / 'seal.json').read_bytes())
        assert sha(publication / 'review-joined.json') == seal['review-joined.json']
        joined = json.loads((publication / 'review-joined.json').read_bytes())
        candidates = [obj for obj in objects(joined) if canonical_hash(obj) == label['published_row_sha256']]
        assert len(candidates) == 1, row['case_id']
        private.append({'case_id': row['case_id'], 'registry_row_unchanged': label,
                        'source_Controller_native_join_unchanged': candidates[0],
                        'baseline_native_text': row['native_text'],
                        'not_a_new_blind_semantic_review': True,
                        'must_not_enter_preread_or_actor_additional_feedback': True})
    # These are direct current-frame observations for control preparation only.
    observations = [
        'Readable search panel. The field shows neon grecarcar, not the old candidate\'s neon greecarcar. The no-results message is a coherent site template.',
        'Current lower listings show phones and pagination. This frame alone does not establish that all earlier frames contained only phones/electronics or lacked people.',
        'Current AIR HEAD TOWBAGON detail visibly shows multiple people, 600.00 $, date 2023/10/03. It does not establish the oldest matching listing or the content of every earlier listing.',
        'Readable furniture grid. Queen Ikea Mattress contains a browser screenshot thumbnail; the old quoted 349.90 is distinct from the original 349.00 read in prior source review. Displayed listing price is 100.00 $. Screenshot-device/task-fit remains a separate question.',
        'Readable home page. Category dropdown exists. Selecting a category is a proposed normal action, not a claim of completed search.',
        'Readable Furniture page. Empty Your search field has a blue border. Typing is a normal proposed next action; this visual source is retained as a focus control.',
        'Readable Farm + garden page with more content below. Future scrolling does not assert a rider was already found.',
        'Readable lower page with 1, 2, 3, >, » and footer. Footer content is coherent; the navigation is a plan, not proof the destination was reached.',
        'Readable Furniture grid showing sofa, chair and bed, with further items partly visible. Scrolling to look for the target is a normal plan.',
        'Readable search panel. The field shows neon grcarcar, matching the old bounded reading. More backspacing is a plan, not an assertion the field was already cleared.',
    ]
    root = HERE / ('proposal-publication-' + str(time.time_ns()))
    root.mkdir()
    for name in ['reading_contract.py', 'prepare_and_test.py', 'freeze_sources.py',
                 'prepare_native_cpu.py', 'prepare_native_cpu_linked02.py', 'publish_preparation.py']:
        shutil.copyfile(HERE / name, root / name)
    for name in ['preread-system.txt', 'actor-feedback-prefix.txt', 'actor-feedback-suffix.txt']:
        shutil.copyfile(proposed / name, root / name)
    save(root / 'PRIVATE-existing-baselines-and-bindings.json', private)
    save(root / 'current-frame-preparation-review.json', {
        'reviewer_count': 1, 'fully_blind': False,
        'ten_current_original_PNGs_actually_viewed_at_original_resolution': True,
        'all54_history_images_newly_semantically_reviewed_in_this_preparation': False,
        'previous_full_source_reviews_referenced_without_changing_labels': True,
        'not_an_efficacy_or_new_model_reply_review': True,
        'rows': [{'case_id': row['case_id'], 'current_PNG_sha256': row['current_image_sha256'],
                  'source_observation': observation} for row, observation in zip(rows, observations)]})
    counts = cpu_summary['prepared_preread_input_token_counts']
    plan = {'time': time.time(), 'condition': 'same-primary-history-image-preread-v1',
            'approval_state': 'pending_user_decision', 'new_condition_authorized': False,
            'formal_new_GUI_authorized': False, 'goal': 'active', 'effectiveness_proven': False,
            'previous_approved_ten_calls_completed_not_reused_as_new_budget': True,
            'sources': str(frozen), 'sources_seal_sha256': sha(frozen / 'seal.json'),
            'proposed_inputs': str(proposed), 'proposed_inputs_seal_sha256': sha(proposed / 'seal.json'),
            'native_CPU': str(cpu), 'native_CPU_seal_sha256': sha(cpu / 'seal.json'),
            'serialization_failure_preservation': str(failure),
            'serialization_failure_seal_sha256': sha(failure / 'seal.json'),
            'selected_prefixes': 10, 'distinct_original_tasks': 5,
            'selection_is_known_source_nonblind_development': True,
            'distinct_original_PNGs': 54, 'image_occurrences_per_case':
                {r['case_id']: len(r['image_occurrences']) for r in rows},
            'current_frame_image_review_count': 10,
            'new_CPU_structure_source_checks': 57, 'native_CPU_prepared_cases': 10,
            'preread_input_tokens': counts, 'preread_input_tokens_sum': sum(counts.values()),
            'new_primary_calls_cap': 20, 'preread_max_output_tokens': 4096,
            'actor_max_output_tokens': 2048, 'per_prefix_preread_calls': 1,
            'per_prefix_actor_calls': 1, 'automatic_retries': 0,
            'seed': 42, 'do_sample': False, 'BF16_SDPA_original_generation_path_preserved': True,
            'generation_schema_enforcer_added': False,
            'original_baselines_reused': True, 'new_GUI_Flash_scorer_paid_calls': 0,
            'actual_new_model_calls_in_this_preparation': 0,
            'main_actor_original_system_and_full_history_and_images_preserved': True,
            'failed_previous_292_token_suffix_not_stacked': True,
            'Flash_single_image_fixed_prompt_YES_NO_no_context_accumulation_unchanged': True,
            'all_preread_images_original_order_including_repeat_occurrences': True,
            'old_assistant_execution_text_and_candidates_excluded_from_preread': True,
            'actor_appends_one_fallible_reading_text_block_to_last_original_user_message': True,
            'new_replies_not_inserted_into_other_prefix_histories': True,
            'only_structure_and_source_IDs_validated_not_visual_truth': True,
            'actual_actor_body_native_CPU_and_first_forward_binding_required_after_real_reading': True,
            'GPU_actual_lease_capacity_full_logit_and_generation_not_tested_here': True,
            'native_WAIT_real_sources_in_selection': 0,
            'WAIT_fixture_only_not_semantic_validation': True,
            'formal_GUI_readiness_from_this_static_preparation': False,
            'new_loader_or_GPU_command_submitted': False,
            'runtime_and_reservation_costs_must_be_measured_no_currency_or_savings_claim': True}
    save(root / 'plan.json', plan)
    table = '\n'.join('|%s|%s / %s|%s|%s|' % (r['case_id'], r['run_id'].replace('flash14-', ''),
                      r['decision'], counts[r['case_id']], len(r['image_occurrences'])) for r in rows)
    report = '''# 历史原图预读：十条离线开发方案（待批准）

拟验证的改变：Flash继续独立接收一张完整截图、固定prompt并返回YES/NO；在主27B生成动作前，额外调用同一个27B一次，只给原任务和全部历史原图，排除旧assistant叙述、行动计划和执行反馈。它输出带图片来源编号的少量原文/可见特征及局限，再作为“可能读错的附加资料”送入保留完整原历史的actor。

这是新增的主模型视觉预读阶段，不是Flash原生新能力，也不是独立模型交叉核验。与旧的当前截图preview、文本叙述索引和同次Flash三问选项不同；本次只准备这个具体条件，不把静态工程检查称为降低Mirage。上一轮已批准10次调用已经全部用完；本方案需要另行批准，不能自动发布新GUI。

## 具体提示和接线

原生英文预读system全文见同目录 `preread-system.txt`；actor追加文本的准确前后文见 `actor-feedback-prefix.txt`、`actor-feedback-suffix.txt`；纯Python接线见 `reading_contract.py`。预读仅描述局部可读字符串、可见特征、位置和不确定性，不下动作/全局最优/全体排除结论。每张原图每次出现都保留一条记录，重复PNG也不合并。JSON来源编号合法只证明来源存在，不能证明读数正确；CPU负向fixture明确表明错误事实仍可能通过结构检查。

actor的原system、完整合法历史、原图、原生动作协议、生成路径和2048输出保留，只在最后原user末尾追加这份原样预读文本及“非事实保证”的固定说明。没有把上一版失败的292-token后缀叠加进来，也不编辑actor回答/动作。新回复不会进入别的固定前缀历史。预读内容动态产生，所以真实actor完整输入此刻尚不存在；每次需先CPU封存实际动态body，再比对实际首次forward的IDs/pixels/grid，不能提前声称已冻结或GPU容量已通过。

## 控制来源和预算

十个已知来源、五个原任务的非盲开发前缀，均不同于已完成的十条T017输入。包含四个已有确定错误来源及六个正常/负例来源；旧标签在PRIVATE文件，仅用于事后比较，不进入两个模型请求。真实完整body、wire、EOS回复、来源seal和原PNG已冻结；十条当前原图已重新查看，历史完整源审透明引用原封存，不冒称54张历史图已在本次重新做语义审查。54张去重原PNG、95次原出现均保留。

|来源|原run / 决策|预读原生输入token|图像出现次数|
|---|---|---:|---:|
''' + table + '''

最多20次新27B调用：每条1次预读（最多4096输出）＋1次actor（最多2048输出），seed42/greedy、原BF16/SDPA及原backend生成路径；两个阶段均不加新语法约束生成器。旧基线直接复用，0 GUI、0 Flash、0评分、0付费、0自动或格式重试。JSON无效、缺帧/错绑、非自然EOS、容量/归属失败均保留为失败，不猜测修补、扩大预算、截历史、缩图或改精度；未得到合法预读的来源不调用其actor。本计划只批准这十个离线前缀，不批准新正式GUI。

新57项CPU结构/来源边界检查通过，十条新预读输入经原生processor实际CPU处理。视觉张量与网格逐字段SHA等于原实际forward记录；原全量raw审计引用原核验时点，没有重复旧队列或全量审计。预读输入为1547至20389 tokens；这些是CPU输入准备结果，不是GPU fit或语义通过。actor的动态附文会增加输入和推理工作；同权重可能重复视觉错误，预读还可能引入新的错误前提、更多探索或影响完成率。

原生CPU准备首attempt因Windows CRLF与远端LF的文件字节不同而中止，0权重/推理；原源码、日志、回执已封存。新关联准备传输冻结文件原字节、核对文件SHA及完整对象后才处理，十条完成。原输入、提示、SHA标准未放松。链接和精确SHA见 `plan.json`。

## 审查和边界

推理后分别审查预读自身的错误/遗漏、actor的全部文字、原生动作及正常探索。先按合法原图/历史封存新标签，再显式join旧标签；一次发生即计，不能由后续修正或后置拒绝删除。未决、原生格式失败、基础设施失败与语义阳性分列。只比较这些固定前缀，不能换算全局触发率、首次错误、完整GUI误拦率或完成率。

当前十条没有真实native WAIT。已有WAIT只是派生CPU解析fixture，不能算真实WAIT语义控制；Flash的NO持续复拍也不会在这次离线调用中得到验证。缺口保留，正式GUI仍不ready。即使开发结果改善，也需另备有对照的完整GUI条件和预算，再由用户决定。

GPU启动前必须重新核实UID、完整命令/start、GPU UUID、外人compute、可用显存及实际继承锁；不抢占、不凭旧PID/空闲当新租约。沿用充裕显存的原BF16布局，所有实际保留卡均计GPU秒，包括未计算时间；独立记录加载、预读、actor、失败与封存区间，不宣称货币、能耗或节省。当前未提交任何模型/GPU启动命令。

本方案状态：待用户批准新增20次离线开发调用；总目标ACTIVE，降低Mirage尚未证明。
'''
    report_path = root / '历史原图预读十条离线开发方案-20261115.md'
    report_path.write_text(report, encoding='utf8')
    heads = [BASE / 'HANDOFF.md', BASE / 'README.md', PARENT / 'CONTINUATION.md', PARENT / 'README.md']
    old = []
    for i, path in enumerate(heads):
        data = path.read_bytes(); old.append((path, data, hashlib.sha256(data).hexdigest()))
        backup = root / 'previous-heads' / ('%02d-' % i + path.name)
        backup.parent.mkdir(parents=True, exist_ok=True); backup.write_bytes(data)
    save(root / 'seal.json', {str(p.relative_to(root)).replace('\\', '/'): sha(p)
                             for p in root.rglob('*') if p.is_file()})
    pointer = {'publication': str(root), 'report': str(report_path), 'seal_sha256': sha(root / 'seal.json'),
               'condition': plan['condition'], 'new_condition_authorized': False,
               'new_calls_cap_pending_approval': 20, 'actual_new_model_GUI_calls': 0,
               'previous_GUI29_and_offline10_completed_immutable': True,
               'goal': 'active', 'effectiveness_proven': False}
    save(HERE / 'publication-current.json', pointer)
    save(PARENT / 'history-preread-preparation-current.json', pointer)
    header = '''## 最新：下一版历史原图预读仅CPU准备完成，新增20次离线调用待用户决定

权威 history-image-preread-preparation-01/publication-current.json。10个不同于旧T017的完整来源前缀/5原任务，54原PNG、95出现均冻结；同一主27B预读只见原task和全部原图，不见旧assistant/action/execution叙述，actor完整原史/原system保留，只追加可能错误的来源读数。唯一Flash仍原独立单图固定YES/NO，不新增JEV或改变Flash。

57新CPU来源/错绑结构检查及10原生CPU输入完成；原视觉张量/grid与原实际forward SHA相同。当前10原图已查看，历史源审引用旧封存，非新全54语义审查。CPU首attempt换行字节SHA失败0权重/调用已保全，新linked02传冻结原字节后完成；未放松来源。0新模型/GPU/GUI/Flash/scorer命令，不称效果/容量通过。结构合法不保证语义；缺真实WAIT/NO复拍资格。

拟议仅10×(预读4096+actor2048)，最多20新27B调用、0自动重试、旧基线复用；动态actor输入须待真实读数后CPU封存/首次forward比对，启动要重新核归属/UUID/compute/显存/继承锁，计全部保留卡成本。上一批准10次已完成用完，不可追加或自动发布正式GUI。新20尚未获批，先用户决定。原29GUI、10离线及全部终局/完整审计不重跑，旧阳性/未决/失败/成本保留，目标ACTIVE/降低未证。以下为历史。

'''
    for path, data, expected in old:
        assert sha(path) == expected, 'Concurrent handoff update; stop instead of overwriting'
        with path.open('w', encoding='utf8', newline='') as stream:
            stream.write(header + data.decode('utf8'))
    print(json.dumps({'publication': str(root), 'report': str(report_path), 'CPU_checks': 57,
                      'native_CPU_cases': 10, 'new_model_GUI_calls': 0, 'approval': 'pending'}))


if __name__ == '__main__':
    main()
