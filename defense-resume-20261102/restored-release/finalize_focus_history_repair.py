"""Verify and seal the two completed repair conditions; never launch inference."""
import ast
import hashlib
import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
PREP = BASE / 'focus-history-repair-development'
SUP = PREP / 'readiness-supplement'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def write(p, value):
    assert not p.exists(), 'Immutable finalization already exists: ' + str(p)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def verify(prep, expected_cases, expected_calls):
    ip = read(prep / 'inspection-current.json')
    assert ip['terminal'] and ip['process'] is None
    assert ip['status']['phase'] == 'completed'
    root = Path(ip['collected_root'])
    assert sha((root / 'terminal-sha256.json').read_bytes()) == ip['terminal_manifest_sha256']
    for name, digest in read(root / 'terminal-sha256.json').items():
        assert sha((root / name).read_bytes()) == digest, name
    post = read(root / 'postexit-evidence.json')
    assert post['process'] is None
    for name, digest in post['postexit_sha256'].items():
        assert sha((root / name).read_bytes()) == digest, name
    ap = read(prep / 'service-audit-current.json')
    ar = Path(ap['directory'])
    assert sha((ar / 'audit.json').read_bytes()) == ap['audit_sha256']
    assert sha((ar / 'sha256.json').read_bytes()) == ap['manifest_sha256']
    for name, digest in read(ar / 'sha256.json').items():
        assert sha((ar / name).read_bytes()) == digest, name
    audit = read(ar / 'audit.json')
    summary = read(root / 'summary.json')
    cases = {r['id']: r for r in summary['results']}
    assert len(cases) == expected_cases
    assert audit['verified_distinct_requests'] == len(audit['records']) == expected_calls
    assert len(summary['calls']) == expected_calls
    assert all(r['natural_eos'] and r['actual_request_and_response_bound'] for r in audit['records'])
    assert all(r['contract_status'] == 'valid' for r in cases.values())
    chains, scope_events, raw = [], [], []
    images = set()
    for case in cases:
        packet = read(root / 'inputs' / (case + '.json'))
        for im in packet['public']['images']:
            assert sha((root / 'images' / (im['sha256'] + '.png')).read_bytes()) == im['sha256']
            images.add(im['sha256'])
        previous = '0' * 64
        events = [json.loads(line) for line in (root / 'journal' / case / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
        for seq, event in enumerate(events):
            payload = {k: v for k, v in event.items() if k != 'sha256'}
            assert event['seq'] == seq and event['previous'] == previous
            assert sha(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()) == event['sha256']
            previous = event['sha256']
            if event['kind'] in {'current_only_execution_history_scope', 'historical_event_source_scope'}:
                scope_events.append({'case': case, 'kind': event['kind'], **event['data']})
            if event['kind'] == 'verifier_raw':
                raw.append({'case': case, 'event_sha256': event['sha256'], **event['data']})
        chains.append({'case': case, 'events': len(events), 'head': previous})
    assert sorted(chains, key=lambda r: r['case']) == sorted(audit['event_chains'], key=lambda r: r['case'])
    return dict(prep=prep, root=root, inspection=ip, service_pointer=ap, audit=audit,
                cases=cases, chains=chains, scope_events=scope_events, raw=raw, images=images)


def main():
    for prep in [PREP, SUP]:
        assert not (prep / 'completed-current.json').exists(), 'Do not refinalize or retry completed controls'
    assert read(PREP / 'user-decision.json')['approved'] is False
    a, b = verify(PREP, 12, 12), verify(SUP, 4, 5)
    assert not a['audit']['format_errors']
    assert len(b['audit']['format_errors']) == 1
    rejected = [r for r in b['scope_events'] if r['reject']]
    assert len(rejected) == 1 and rejected[0]['case'] == 'b01'
    assert rejected[0]['kind'] == 'current_only_execution_history_scope'
    assert not any(r['reject'] for r in b['scope_events'] if r['kind'] == 'historical_event_source_scope')
    assert [a['cases']['f%02d' % n]['verdict']['status'] for n in range(1, 7)] == ['usable', 'limited'] * 3
    assert a['cases']['h04']['native_WAIT_excluded']
    assert a['cases']['h04']['verdict']['pure_wait']
    assert b['cases']['b03']['verdict']['claims'][1]['status'] == 'insufficient'
    assert b['cases']['b04']['verdict']['claims'][0]['status'] == 'contradicted'
    assert b['cases']['b04']['verdict']['claims'][0]['evidence'][0]['image_index'] == 1
    requests = [r['receipt'] for group in [a, b] for r in group['audit']['records']]
    assert len(set(requests)) == len(requests) == 17 <= 24
    assert len(a['images'] | b['images']) == 6
    # Supplement changed only Controller/imports and the new scope module. Keep all
    # top-level validators, data classes and original budget definitions identical.
    trees = []
    for group in [a, b]:
        tree = ast.parse((group['root'] / 'release/defense/core.py').read_text(encoding='utf-8'))
        trees.append({node.name: ast.dump(node, include_attributes=False) for node in tree.body
                      if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name != 'Controller'})
    assert trees[0] == trees[1]
    for filename in ['defense/prompts.py', 'defense/schema.py', 'defense/http_backend.py',
                     'defense/qwen_backend.py', 'run_vwa_pilot.py', 'native-vwa-request.json']:
        assert (a['root'] / 'release' / filename).read_bytes() == (b['root'] / 'release' / filename).read_bytes(), filename
    rows = [
        {'id': 'f01/f02', 'review': 'Keyword蓝框读为usable，普通灰框limited；可见焦点线索匹配，不证明点击因果或允许任意typing。'},
        {'id': 'f03/f04', 'review': 'Your search蓝框/普通框正确区分；同站点配对，不是独立任务。'},
        {'id': 'f05/f06', 'review': 'City蓝框/普通框正确区分；City焦点不能替代Keyword目标焦点。'},
        {'id': 's01', 'review': '首页可读；“Search has not been executed”历史断言无根据，且随后说无法确认是否搜索，原失败保留。'},
        {'id': 's02', 'review': '当前铜制查询和1–12/350读对；No evidence是证据资格限定，不自动当never-search断言。'},
        {'id': 'h01', 'review': '实际先前篮球结果图反驳无先前结果；当前Keyword点击支持。action reason把候选增强成no results existed且尾句未完，不能算全语义通过。'},
        {'id': 'h02', 'review': '失败：输入框已有basketball不证明搜索执行，历史never-search应insufficient而非已反证；action reason自然EOS仍尾句未完。'},
        {'id': 'h03', 'review': '无证据STOP被拒；但当前铜制页不反证所有先前检视，历史已完成声明应insufficient。plan-only不等于执行；reason过强且未完。'},
        {'id': 'h04', 'review': '正确引用人工早先计划，未认证完成；pure nativeWAIT排除。不是自然actorWAIT或原生轨迹控制。'},
        {'id': 'b01', 'review': '首次原始回复仍断言search has not been submitted；新current-only约束真实拒绝，使用原1formatretry后改为No confirmation。原错未抹去；最终readiness仍没明确报告Keyword蓝框。'},
        {'id': 'b02', 'review': 'City焦点框、当前铜制查询/350列表有依据；may still be settling是保留可能性的假设，不是可见loading阳性。'},
        {'id': 'b03', 'review': '无早先图时将当前铜制事实supported、历史never-search insufficient，未以当前像素反证过去。主历史来源约束未触发；不能归因它造成模型改进。'},
        {'id': 'b04', 'review': '提供真实先前篮球结果图时，历史无结果声明contradicted并引用reference1；当前点击与意图分开，未一律弃权。归一化178,273落到227.84,196.56像素，位于当前Your search框。点击不会自行清空文字，reason的clear应理解后续目的而非已完成清空。'},
    ]
    totals = {key: sum(group['audit'][key] for group in [a, b]) for key in
              ['input_tokens', 'output_tokens', 'summed_generation_seconds']}
    report = BASE / '焦点与历史推断修复真实预检结果-20261028.md'
    out = PREP / ('final-review-' + str(time.time_ns()))
    out.mkdir()
    review = {'rows': rows, 'calls': 17, 'natural_eos': 17, 'logical_controls': 16,
              'unique_images': 6, 'format_retries': 1, 'semantic_pass_count': None,
              'current_only_online_rejections': 1, 'main_historical_source_online_rejections': 0,
              'original_prompt_only_history_failures_preserved': ['s01', 'h02', 'h03'],
              'all_sources_independently_image_reviewed': True, 'reviewer_count': 1,
              'private_expectations_sent_to_checker': False, 'authored_WAIT_excluded': True,
              'new_natural_actor_WAIT': False, 'same_live_actor_recovery_tested': False,
              'fullGUI_authorized': False, 'formal_release': False,
              'new_actor_calls': 0, 'model_GUI_actions': 0, 'official_scores': 0, 'paid_API_calls': 0,
              'invariants': 'Original strict validators/Limits/native request/runner/prompts/backend unchanged between repair conditions; Controller supplemental source eligibility added. Candidate-blind projection pre-existed.',
              'tradeoff': 'Conservative source eligibility can withhold valid events shown by a current-screen history/log UI. Eligible earlier assistant text is not execution proof. Regex narrow, misses paraphrases; unflagged is not semantic approval. Source-policy rejection recorded in original format_retry channel is not malformed JSON.',
              'condition': 'Two separate selected nonblind development conditions,12 prompt-only calls then5 supplemental calls. Logged-out same-site sources, repeated pixels/phases, authored candidates/context. No same-input paired causal comparison/general semantic accuracy/Mirage efficacy.',
              'cost_scope': 'Summed generation tokens/seconds only; excludes loading/source collection/CPU/analysis; not wall-time/currency/energy. Current5GPU deployment not historical7GPU bitwise/cost equivalent.',
              'raw_supplemental_replies': b['raw'], **totals}
    write(out / 'review.json', review)
    text = '''# 焦点与历史推断修复：真实开发预检结果

结论：专用焦点读取在这组蓝框/普通框对照上读对；仅改提示不足以修复历史推断。新增来源约束真实暂扣了一次无证据的“搜索尚未提交”，原预算重试后保留不确定性。当前证据支持保留这个隔离修复版本继续验证，尚不能宣布完整防御、历史推断或GUI恢复已经修好。

用户选择“先修复焦点和历史推断问题”。上一完整GUI proposal未授权，未启动。新版本为evidence-v4.0.1-dev-focus-history-scope与独立补充evidence-v4.0.2-dev-current-only-scope；不覆盖旧终局。

|部分|实际结果|限制|
|---|---|---|
|Keyword/Your search/City三对焦点读取|6次均正确区分蓝框与普通边框|单站点3配对，非6独立任务；City焦点不证明Keyword目标可输入|
|第一轮提示修复|12调用/12自然EOS/0重试|s01、h02、h03历史范围仍失败；拒绝STOP不表示解释都正确|
|当前画面历史断言约束|b01首次断言搜索没提交，真实暂扣；原1次重试后改为无法确认|首次错误仍完整计留；不是JSON解析失败，是来源规则借用原重试通道|
|无早先图历史控制b03|当前铜制结果supported；从未篮球搜索insufficient|模型已自行保留不足，主历史来源约束0次在线拒绝，不能归因其带来改进|
|有真实先前图控制b04|引用先前篮球结果图反驳“从未出现结果”；当前点击与意图分开|非完整actor轨迹；点击不会自行清空输入，reason中clear是后续目的，非完成事实|
|readiness剩余问题|b02读出City焦点；b01不再断言历史未执行|b01仍没明确描述Keyword蓝框；专用focus成功不能替代readiness全语义通过|

## 逐项独立审查

'''
    text += '\n\n'.join('**' + row['id'] + '**：' + row['review'] for row in rows)
    text += f'''

## 方法、取舍与边界

原strict validators、Limits预算、native prompt/schema/runner/backend保留。当前画面的空输入、不同查询、缺少结果不再应当推出过去从未执行；计划/报告与实际执行分开。已有current-task/recent-action/feedback/current-image候选盲投影未改变，不能包装为新方法。原图/完整公开历史不截断，BF16/SDPA与4096核验输出/1formatretry保持。补充Controller已在隔离版本接入两类约束，未部署到正式完整GUI。

辅助current-only输出只对窄范围确定执行断言暂扣；主核验对含明确过去事件的确定判断检查是否有合资格较早来源。两者不修改原verdict/JSON，不补正确页码、相反历史或动作。早先assistant话语只是报告/计划，不自动证明执行；合资格来源不保证真假。保守策略可能误拦当前屏幕内日志/历史记录所证明的事件，正则也会漏过改述。未命中不等于语义批准，尚不能给出误拦率或全面正确性。

已知第一轮回复的离线工程重放只会暂扣s01/h02/h03，属于已知失败重放，不计新在线成功。原有167CPU本地/远端工程检查通过，补充34项本地/远端通过，补充版本原122相关测试也通过；CPU数量不作语义准确率。

16逻辑控制共{len(requests)}真实调用，全部自然EOS，1次原格式重试；12调用与5调用分属两个根。只有6唯一原始1280×720图，配对和跨phase复用不构成独立任务/视觉复制。来源为logged-out脚本采集，非原logged-in native actor轨迹；prior-results和query-ordinary同PNG。另一个查询实际返回350铜制商品，绝不是no-results。PRIVATE期待不进入checker。h03/h04为人工plan-only上下文，h04人工nativeWAIT依用户口径排除，不称自然actorWAIT。没有可见loading阳性、live actor typing恢复或任务效力试验。

0新actor生成、0模型GUI动作、0官方评分、0付费API。17个实际service完整request/inputIDs/generation/outputIDs/EOS/replies/原图绑定，16条SHA链73事件验证，两个worker已退出；所有终局及失败原文保留。第一轮终局SHA {a['inspection']['terminal_manifest_sha256']}；补充终局SHA {b['inspection']['terminal_manifest_sha256']}。

输入{totals['input_tokens']:,}、输出{totals['output_tokens']:,}token，累计生成{totals['summed_generation_seconds']:.4f}秒；不含加载、来源采集、CPU及分析，不是墙钟/货币/能耗。当前UID1033原27B五卡BF16/SDPA服务与历史七卡单列，无逐位/成本等价假设。两轮合计17/24调用，剩余额度不得重跑已完成控制。

下一步需要在原总预算内验证焦点与目标字段/typing联动、计划与实际历史事件冲突、自然actorWAIT和完整GUI恢复。先完成这些具体准备与条件取舍，上一完整GUI proposal继续未授权；不自动启动或重问旧问题。其他60native/live adapters及正式防御效力仍未完成，monitor保持ACTIVE，旧队列与27B注意力终局不重启。
'''
    assert not report.exists()
    report.write_text(text, encoding='utf-8')
    outputs = []
    for group in [a, b]:
        pointer = {'directory': str(out), 'remote_root': group['inspection']['root'],
                   'terminal_root': str(group['root']), 'terminal_manifest_sha256': group['inspection']['terminal_manifest_sha256'],
                   'service_audit_sha256': group['service_pointer']['audit_sha256'],
                   'calls': len(group['audit']['records']), 'logical_controls': len(group['cases']),
                   'natural_eos': len(group['audit']['records']), 'format_retries': len(group['audit']['format_errors']),
                   'review_sha256': sha((out / 'review.json').read_bytes()), 'report': str(report), 'report_sha256': sha(report.read_bytes()),
                   'fullGUI_authorized': False, 'formal_release': False, 'completed_controls_must_not_retry': True}
        write(group['prep'] / 'completed-current.json', pointer)
        outputs.append(pointer)
    combined = {'conditions': outputs, 'calls': 17, 'logical_controls': 16, 'natural_eos': 17,
                'format_retries': 1, 'aggregate_original_cap': 24, 'unused_cap_not_for_terminal_retries': 7,
                'current_only_online_rejections': 1, 'main_historical_source_online_rejections': 0,
                'report': str(report), 'report_sha256': sha(report.read_bytes()), 'review_directory': str(out),
                'review_sha256': sha((out / 'review.json').read_bytes()), 'formal_release': False,
                'fullGUI_authorized': False, 'monitor': 'ACTIVE', **totals}
    write(PREP / 'repair-combined-current.json', combined)
    write(out / 'sha256.json', {'review.json': sha((out / 'review.json').read_bytes()), str(report): sha(report.read_bytes()),
                              **{str(group['prep'] / 'completed-current.json'): sha((group['prep'] / 'completed-current.json').read_bytes()) for group in [a,b]},
                              str(PREP / 'repair-combined-current.json'): sha((PREP / 'repair-combined-current.json').read_bytes())})
    print(json.dumps(combined, ensure_ascii=False))


if __name__ == '__main__':
    main()
