"""Write the human conclusion from the independently verified paired evidence."""

from collections import Counter

from summarize import CONDITIONS, COURSE_NAMES, VERSIONS, cohort


_DOSE = 'attempts_with_real_injected_change'
_LEAK = 'injected_change_reached_actor_actual_forward'
_RECOVERY = 'independently_normal_image_reached_actor_after_loop'


def ratio(n, total):
    assert 0 <= n <= total
    return f'{n}/{total}' if total else '—（无实际样本）'


def render_usable_capture_coverage(cycles):
    coverage = cycles['independently_usable_unchanged_captures_on_arm']
    initial, scopes = coverage['eligible_initials'], coverage['by_scope']
    verdicts = cycles['actual_Flash_verdicts']
    incomplete = sum(v['n'] for v in verdicts if v['independent_image_quality'] == 'visually_incomplete')
    unknown = sum(v['n'] for v in verdicts if v['independent_image_quality'] in ('unresolved', 'unreviewed'))
    return [f"开启臂的所有条件共出现 {initial['captures']} 次独立确认可用、未被替换的初帧"
            f"（{initial['distinct_original_PNGs']} 张不同原图；正常条件 {scopes.get('clean_initial', {}).get('captures', 0)} 次，"
            f"注入条件中的正常初帧 {scopes.get('injection_arm_initial', {}).get('captures', 0)} 次）。"
            f"各层对这些初帧拒绝 {initial['rejected_by_any_guard']} 次；"
            f"Flash 返回 YES {initial['flash_yes']} 次，"
            f"{initial['reached_actual_first_forward']} 次进入真实主模型前向，"
            f"{initial['delivered_actor_natural_EOS']} 次交付了自然结束的回复。",
            f"本批 Flash 共返回 {sum(v['n'] for v in verdicts)} 次明确判定；其中独立审图判为画面不完整的帧 {incomplete} 次，"
            f"未决或未审帧 {unknown} 次。正常图放行的分母不能用来估计 Flash 对异常图的检出率。"]


def render(rows, pairs, groups, overall, normal_alignment, timing, isolation, tables, *, gate_cycles,
           followup=None, native=None, stale_boundary=None):
    slot_count = len(rows)
    sealed = overall['sealed_terminals']
    complete = sealed == slot_count
    score_pairs = sum(p['both_officially_scored'] for p in pairs)
    lines = ['# Flash 截图防御配对实验：' + ('结论' if complete else '阶段预览'), '']
    if not complete:
        lines += ['预览使用已封存轨迹。其余槽位未完成，不作最终判定。', '']
    lines += [f"固定 {len({r['task_id'] for r in rows})} 个 VWA Classifieds 任务，"
              f"{len(pairs)} 对、{slot_count} 个原始槽位。已核验 {sealed} 条，"
              f"其中 {overall['officially_scored']} 条有原生评分，{overall['non_scored_terminals']} 条无评分"
              f"（{overall['infrastructure_failures']} 条为技术中断）；{score_pairs} 对两臂均有评分。", '',
              '**截图是否被挡、是否实际恢复。** 分母为对应臂真正收到异常交付的次数。'
              '缺图包括当前图块缺失、历史图仍在；复拍成功必须有同一决策的正常原图实际进入主模型。'
              '以下跨版本合计只描述机制证据，各版本和未触发情况见明细。', '',
              '| 实际异常 | 关闭：异常到达主模型／注入 | 开启：异常到达主模型／注入 | 开启：正常图闭环／注入 |',
              '| --- | ---: | ---: | ---: |']
    for condition in CONDITIONS[1:]:
        selected = [g for g in groups if g['condition'] == condition]
        def total(arm, field):
            return sum(g[arm][field] for g in selected)
        n_off, n_on = (total(a, _DOSE) for a in ('off', 'on'))
        lines.append(f'| {COURSE_NAMES[condition]} | {ratio(total("off", _LEAK), n_off)} | '
                     f'{ratio(total("on", _LEAK), n_on)} | {ratio(total("on", _RECOVERY), n_on)} |')
    outcomes = [p['actual_altered_observation'] for p in pairs if p['fired_and_matching_exact_native_prefix']
                and all('decision' in a for a in p['actual_altered_observation'].values())]
    paired_closure = sum(q['off']['altered_observation_at_actual_forward'] and q['on']['normal_recapture_at_actual_forward']
                         for q in outcomes)
    stages = overall['blocked_changed_image_by_stage']
    evaluated = overall['changed_initial_image_with_actual_Flash_verdict']
    lines += ['', f'两臂确实都遭遇异常且注入前原图和动作相符的 {len(outcomes)} 对中，'
              f'{paired_closure} 对同时证实关组坏图进入、开组同决策送入正常复拍图。'
              f"实际拦截来自存在检查 {stages.get('precheck_decision', 0)} 次、"
              f"采集回执 {stages.get('capture_receipt_decision', 0)} 次、"
              f"Flash 返回 NO {stages.get('gate_decision', 0)} 次。"
              f'Flash 实际判定过 {sum(evaluated.values())} 张改变的初帧；它在复拍图上返回 YES 不计入该数。', '',
              f"严格核对后，有 {isolation['exact_input_isolated_pairs']} 对实际主模型输入只差当前图，"
              '此前原始观察、合法历史、回复和动作均对齐。这些配对中，'
              f"{isolation['same_immediate_reply_on_isolated_pairs']} 对当轮原回复相同，"
              f"{isolation['same_immediate_native_ack_on_isolated_pairs']} 对当轮执行了相同动作且回执一致。"
              '两种结果都保留；恢复正常输入不必然改变当轮回复或任务分数。', '']

    altered_replies = [s for r in rows for s in (r['steps'] or [])
                       if s['known_injected_dose_at_actual_forward']]
    assert len(altered_replies) == overall[_LEAK]
    at_dose = Counter()
    for step in altered_replies:
        label = step['actor_semantic_label']
        if not step['actor_reply_EOS']:
            at_dose['no_EOS'] += 1
        elif label is None:
            at_dose['unreviewed'] += 1
        elif label == 'definite':
            at_dose['definite'] += 1
        elif label == 'pure_native_WAIT_excluded':
            at_dose['excluded_wait'] += 1
        elif label == 'unresolved' or step['also_unresolved_claims']:
            at_dose['unresolved'] += 1
        else:
            assert label == 'no_definite_positive'
            at_dose['no_definite_positive'] += 1
    assert sum(at_dose.values()) == len(altered_replies)
    assert at_dose['definite'] == overall['definite_Mirage_on_an_actually_injected_observation']
    lines += [f'对异常确实到达主模型的 {len(altered_replies)} 次，仅看当轮：'
              f"确定 Mirage {at_dose['definite']} 次，未决 {at_dose['unresolved']} 次，"
              f"未见确定事件 {at_dose['no_definite_positive']} 次，纯原生 WAIT 排除 {at_dose['excluded_wait']} 次，"
              f"无自然终止回复 {at_dose['no_EOS']} 次，待审 {at_dose['unreviewed']} 次。"
              '这是实际暴露后首轮的诊断计数，整条轨迹的 Mirage 见下表。', '',
              '**正常操作的代价。** 等待对照只统计正常条件中独立确认可用的真初帧，从图像就绪到提交主模型。'
              '逐帧观察来自少数重复决策任务，零次误拦仅说明这批未观察到。', '',
              '| 版本 | 关闭：误拦／正常初帧 | 开启：误拦／正常初帧 | 严格对齐的任务数及额外等待中位数 |',
              '| --- | ---: | ---: | ---: |']
    aligned = {x['version']: x for x in normal_alignment['within_task_wait_by_version']}
    for g in (x for x in groups if x['condition'] == 'clean_control'):
        waits = aligned.get(g['version'])
        delay = (f"{waits['tasks_with_exact_normal_prefix']} 个，{waits['median_of_task_medians_seconds']:+.3f} 秒"
                 if waits else '—（无对齐时间）')
        counts = [ratio(g[a]['false_rejections_of_independently_normal_initial_images'],
                        g[a]['independently_normal_initial_images']) for a in ('off', 'on')]
        lines.append(f"| {g['version']} | {counts[0]} | {counts[1]} | {delay} |")
    lines += ['', *render_usable_capture_coverage(gate_cycles)]

    def rates(g):
        n = g['officially_scored']
        c = g['scored_trajectory_Mirage_label_counts']
        definite = c.get('definite', 0)
        unresolved = n - definite - c.get('fully_reviewed_no_definite', 0) - c.get('only_native_WAIT', 0)
        assert unresolved >= 0
        return ratio(g['official_1'], n), ratio(definite, n), unresolved

    lines += ['', '**整条 GUI 轨迹的效果。** 下表按版本保留所有原生评分，包括未触发和有评分的动作格式失败。'
              '未决不填成无 Mirage，技术中断不填成官方 0。对内方向和不确定性按同版本、同条件、同任务见明细；不合并为跨版本效果。', '',
              '| 版本 | 官方 1／有评分（关；开） | 确定 Mirage／有评分（关；开） | Mirage 未决（关／开） | 配对官方开胜／关胜／平 |',
              '| --- | --- | --- | ---: | ---: |']
    for version in VERSIONS:
        vs = [r for r in rows if r['version'] == version]
        off, on = (rates(cohort([r for r in vs if r['arm'] == a])) for a in ('off', 'on'))
        wins = Counter(1 if p['official_difference_on_minus_off'] > 0 else -1 if p['official_difference_on_minus_off'] < 0 else 0
                       for p in pairs if p['version'] == version and p['both_officially_scored'])
        lines.append(f'| {version} | {off[0]}；{on[0]} | {off[1]}；{on[1]} | {off[2]}／{on[2]} | '
                     f'{wins[1]}／{wins[-1]}／{wins[0]} |')

    n_informative = 0
    red, inc = [], []
    for g in groups:
        m = g['paired']['all_both_scored_pairs_Mirage']
        lo, hi = m['task_weighted_on_minus_off_bounds']
        key = f"{g['version']} · {COURSE_NAMES[g['condition']]}（{m['tasks']} 个任务）"
        if lo is None:
            continue
        n_informative += 1
        if hi < 0:
            red.append(key)
        elif lo > 0:
            inc.append(key)
    lines += ['', f'{n_informative} 个有配对证据的版本 × 条件分组中，保留语义未决后的配对差界限全为负的组：'
              + ('、'.join(red) if red else '无') + '；全为正的组：' + ('、'.join(inc) if inc else '无') + '。'
              '这个界限描述标签未决能改变多少，不能当作抽样置信区间。']
    t = timing['all_versions_counts_only']['all_sealed_including_unscored']
    current = t['frame_at_first_confirmed_definite']
    usable = sum(current.get(k, 0) for k in ('independently_usable_current_image', 'independently_usable_recap_at_actual_forward'))
    total = t['Mirage_status'].get('definite', 0)
    lines += [f'在 {total} 条有确定 Mirage 的封存轨迹中，{usable} 条的首次确认错误出现在独立确认可用的图像上。'
              f"在所有封存轨迹的回复中，有 {overall['normal_frame_semantic_errors']} 条可用图上的确定语义错误；"
              f"另计 {overall['separate_prose_native_direction_conflicts']} 条叙述与原生方向相反，两类可重叠。"
              '正常图上的主模型误读不计作截图门控漏拦；错误出现顺序不能单独判定原因。', '']
    if followup is not None:
        verified = followup['all_confirmed_definite']
        assert followup['reviewed_slots'] == sealed and verified['trajectories'] == total
        actions, revisions = verified['native_execution'], verified['later_revision']
        assert sum(actions.values()) == sum(revisions.values()) == verified['definite_replies']
        lines += [f"对 {verified['definite_replies']} 条确定事件的原回复继续核对动作和后续："
                  f"确认错误动作且原生执行返回成功 {actions.get('reviewed_wrong_action_returned_ok', 0)} 条，"
                  f"动作返回失败 {actions.get('native_environment_returned_failure', 0)} 条，"
                  f"动作执行返回成功、但未见确定动作错误 {actions.get('native_action_ok_no_definite_action_error', 0)} 条，"
                  f"已执行动作是否错误仍未决 {actions.get('native_action_ok_validity_unresolved', 0)} 条，"
                  f"没有环境动作回执 {actions.get('no_native_environment_action', 0)} 条。"
                  f"后续确认纠正了同一主张 {revisions.get('confirmed_self_correction', 0)} 条，"
                  f"纠正未决 {revisions.get('possible_revision_unresolved', 0)} 条，"
                  f"有后续回复但未确认纠正 {revisions.get('no_confirmed_self_correction', 0)} 条，"
                  f"无后续实际交付回复 {revisions.get('no_later_delivered_reply', 0)} 条。"
                  '这些是已确认语义错误的逐回复计数，可能来自同一任务或重复输入；纠正不撤销首次错误。'
                  '详见[动作与后续纠正证据](mirage-followup.json)。', '']
    if native is not None:
        assert native['sealed_slots'] == sealed and native['official_score_receipts'] == overall['officially_scored']
        lines += [f"[浏览器归档和原生评分核验](native-execution.json)覆盖 {native['browser_traces']}/{sealed} 条终局。"
                  f"{native['controller_actions']} 次控制器动作记录中，{native['browser_parameter_bound_actions']} 次匹配归档中的原生命令及其参数，"
                  f"{native['browser_operation_only_actions']} 次只核到操作类型，"
                  f"{native['unreconciled_controller_actions']} 次未能联结；"
                  f"浏览器返回错误 {native['browser_bound_actions_returned_error']} 次，"
                  f"另有 {native['unbound_extra_browser_operations']} 次归档操作没有对应的控制器动作记录。"
                  '浏览器返回成功没有证明正确操作或页面发生预期变化，官方分沿用原始 URL 评估。', '']
    lines += ['这批旧图试验只覆盖传输时替换。静态页连续两次采集也可能字节相同；VWA 中有真实页底滚动后像素不变、'
              '新回执和 Flash 均通过、两帧均进主模型的实例。']
    if stale_boundary is not None:
        separate = stale_boundary['separate_signed_early_Chromium_panel']
        assert stale_boundary['sealed_VWA_slots'] == sealed and not separate['part_of_the_frozen_VWA_100_slots']
        trials = separate['temporally_delayed_trials']
        n_recovered = sum(t['same_action_recovered_after_withhold'] for t in trials)
        n_early = sum(t['early_holds'] for t in trials)
        fast = separate['fast_normal_control_pass']
        lines += ['', f'独立 Chromium 双帧实验另测回执有效的早拍：提交前一张图、实际动作和本轮图，'
                  f'在 {len(trials)} 条延迟动作中暂扣 {n_early} 张真实早拍图，{n_recovered} 条复拍后把正常图送入真实主模型；'
                  f'快速更新对照首帧正常放行 {sum(fast.values())}/{len(fast)}。'
                  '这组有意控制渲染延时、没有官方任务评分，且使用了不同门控条件；不并入 VWA 的分母。'
                  '[两类旧帧及相同像素的核验数据](stale-boundary.json)。']
    lines += ['', '持续坏图和跨站点泛化未在这批检验。结论还受固定任务数、动作格式变化以及模型精度切换限制。', '',
              f'[按条件、按版本的完整配对表]({tables}) · [代表、失败及边界轨迹](代表轨迹.md) · '
              '[门控与实际前向](gate-cycles.json) · [当前图差异核验](image-isolation.json) · '
              '[逐轨迹首次错误](mirage-timing.json) · [核验索引](index.json)', '']
    return '\n'.join(lines)
