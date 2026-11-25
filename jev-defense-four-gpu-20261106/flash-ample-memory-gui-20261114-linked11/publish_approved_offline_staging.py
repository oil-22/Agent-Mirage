"""Publish approved scope and immutable receipts; cannot submit inference."""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from control import BASE, HERE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def bind(p):
    return {'path': str(p), 'sha256': sha(p)}


def verify(root, seal='seal.json'):
    expected = load(root / seal)
    assert expected and all(sha(root / name) == h for name, h in expected.items())


def main():
    prep = HERE / 'evidence-discipline-offline-preparation-01'
    assert not (prep / 'submission.json').exists()
    stage = load(prep / 'stage-receipt.json')['result']
    build = load(prep / 'build-receipt.json')
    assert build['manifest_sha256'] == stage['manifest_sha256'] == sha(prep / 'package/offline-manifest.json')
    assert build['files'] == stage['files'] == 83
    assert not stage['worker_submitted'] and stage['new_model_GPU_GUI_calls'] == 0
    authorization = load(HERE / 'evidence-discipline-development-authorization-current.json')
    decision_path = Path(authorization['authorization']) / 'decision.json'
    assert sha(decision_path) == authorization['decision_sha256']
    decision = load(decision_path)
    assert decision['authorized'] and decision['max_new_primary_model_calls'] == 10
    assert decision['existing_29_GUI_must_finish_first'] and not decision['formal_changed_GUI_authorized']
    assert sha(Path(decision['plan'])) == decision['plan_sha256']
    checks = prep / 'CPU-boundaries-1794658892064929500'
    verify(checks)
    assert load(checks / 'result.json')['tests_passed'] == 33
    native = HERE / 'live-evidence-incremental-1794659702709565900'
    verify(native)
    summary = load(native / 'summary.json')
    flash = HERE / 'Flash-CPU-increment-1794659207445110300'
    verify(flash)
    terminals = HERE / 'terminal-audit-1794659327783558600.json'
    terminal_result = load(terminals)['result']
    assert len(terminal_result['terminals']) == 11
    assert not any(r['infrastructure_failure'] or r['cleanup_error'] for r in terminal_result['terminals'])
    semantic = load(HERE / 'semantic-review-current.json')
    assert sha(Path(semantic['publication']) / 'seal.json') == semantic['seal_sha256']
    verify(Path(semantic['publication']))
    ts = time.time_ns()
    pub = HERE / ('approved-offline-staging-publication-' + str(ts))
    pub.mkdir()
    heads = [BASE / 'HANDOFF.md', BASE / 'README.md', HERE / 'CONTINUATION.md', HERE / 'experiment-current.json']
    previous = {}
    (pub / 'previous-heads').mkdir()
    for p in heads:
        previous[p] = p.read_bytes()
        (pub / 'previous-heads' / p.name).write_bytes(previous[p])
    stamp = datetime.fromtimestamp(ts / 1e9, timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S +08:00')
    status = {
        'time': ts / 1e9, 'goal': 'active', 'expected_current_GUI': 29,
        'sealed_GUI_terminals_at_audit': 11, 'terminal_audit': bind(terminals),
        'native_evidence': bind(native / 'summary.json'),
        'cumulative_native_main_replies': summary['cumulative_verified_main_replies'],
        'cumulative_native_Flash_replies': summary['cumulative_verified_Flash_replies'],
        'old_raw_checks_referenced_at_their_recorded_times': True,
        'old_raw_tensors_rehashed_by_latest_increment': False,
        'final_full_postexit_rehash_still_required': True,
        'actual_processes_and_held_locks_at_audit': summary['actual_processes'],
        'Flash_CPU_cumulative_report': bind(flash / 'cumulative-report.json'),
        'GUI_snapshot': summary['GUI_status'], 'GUI_snapshot_is_not_atomic_multi_host': True,
        'snapshot_time': summary['snapshot_time'], 'audit_finished_time': summary['audit_finished_time'],
        'approved_development': {
            'decision': bind(decision_path), 'plan_sha256': decision['plan_sha256'],
            'package_manifest_sha256': build['manifest_sha256'], 'files': 83,
            'build_receipt': bind(prep / 'build-receipt.json'), 'stage_receipt': bind(prep / 'stage-receipt.json'),
            'new_CPU_guard_tests': 33, 'CPU_receipt': bind(checks / 'result.json'),
            'remote_package': stage['remote_package'], 'submitted': False, 'new_model_calls': 0,
            'max_new_primary_calls': 10, 'max_output_tokens': 2048,
            'native_input_increment_per_call': 292, 'existing_29_GUI_must_finish_first': True,
            'new_Flash_GUI_scorer_paidAPI_calls': 0, 'automatic_retries': 0,
            'baseline_replies_reused': True, 'frozen74_native_sources_unchanged': True,
            'main_physical_GPUs': list(range(7)), 'reserved_GPU_cost_count_including_idle7': 8,
            'submission_script': bind(HERE / 'submit_offline_development.py'),
            'formal_changed_GUI_authorized': False,
            'not_capacity_semantic_or_efficacy_proof': True,
        },
        'latest_semantic_publication': semantic,
        'Mirage_reduction': None, 'defense_effectiveness_proven': False,
        'current_GUI_experimental_conditions_changed': False,
        'new_model_GUI_calls_by_publication': 0,
    }
    save(pub / 'status.json', status)
    (pub / 'publisher-source.py').write_bytes(Path(__file__).read_bytes())
    name = '十条离线预检批准与只准备未提交-20261114.md'
    text = f'''# 十条离线开发预检已批准，待当前29条GUI全部结束

截至北京时间{stamp}，当前原版完整GUI已有11/29条封存终局，终局审计未见基础设施或cleanup失败。最新原生输入审计累计核对205份主回复、102份Flash回复，含完整接受历史、实际prepared/first-forward IDs、pixels、grid、生成配置、EOS、回复seal和事件链。增量新核10份主回复；旧原始张量引用各自已封存检查时间，没有宣称本次重新全量哈希。主17锁、Flash9锁及UID/完整命令/start/UUID/实际compute进程已核。最新审计快照正在T058正常图像baseline第19决策；它不是后续全部调用的审计。

用户已批准固定10条离线开发预检，decision SHA `{sha(decision_path)}`，方案SHA `{decision['plan_sha256']}`。只给原主system附加已批准的通用证据约束，每条增加292个原生输入token；固定10个完整前缀、最多10次新27B调用、每次2048输出，原seed42/greedy/BF16/SDPA、原图和完整历史保留。旧基线回复直接复用，0自动重试，0 Flash/GUI/评分/付费API调用。当前29条GUI保持原版。

83文件包已封存并远端逐文件验证，manifest `{build['manifest_sha256']}`；其中原74份原生源码字节相同。33项新CPU检查只核对资源归属、锁、完成前置、一次提交/调用上限和输入张量边界。未运行新权重加载、容量/数值生成或语义推理，**尚未提交**。它们不是33项语义或效果通过。

只有当前29条GUI完整正常结束，全部终局seal/链通过、原GUI/main/Flash/launcher实际退出，再重新核对原holder、所有GPU UUID/无外来compute、空闲显存和继承锁，才运行新的一次性离线入口。主使用0–6，7空闲仍在原锁保留内；成本按8张实际保留卡记。旧内存/GUI/容量检查/完成控制均不重跑，不抢占外人。

最新语义权威见`semantic-review-current.json`及其链接的T058旧帧配对报告；此前T017两个配对结果保留。T058两臂完整同轨迹，末条跨搜索范围的无结果推断仍未决，不能把无实际反例当无Mirage。T017正常图像配对曾发生相同确定错误；旧帧配对一臂存在未决，另一臂本范围无确定错误，但首张图已不同，且均无NO/复拍，不能归因门控降低。现有证据仍未证明可复核的整体Mirage降幅。

Flash继续每次完整单图+固定通用问，独立YES/NO，不含任务/主历史/候选/前图/KV。YES同PNG给主模型，NO持续同环境复拍直到YES或手停；技术故障不是NO。批准范围仅10条离线开发预检，**不包括正式新GUI条件**。仍需独立负例/WAIT/正常操作与任务完成评估；目标ACTIVE。
'''
    (pub / name).write_text(text, encoding='utf8')
    save(pub / 'publication-seal.json', {str(p.relative_to(pub)): sha(p) for p in pub.rglob('*') if p.is_file()})
    pointer = {'publication': str(pub), 'status': str(pub / 'status.json'), 'status_sha256': sha(pub / 'status.json'),
               'report': str(pub / name), 'report_sha256': sha(pub / name),
               'publication_seal_sha256': sha(pub / 'publication-seal.json'), 'goal': 'active',
               'Mirage_reduction': None, 'time': ts / 1e9}
    head = f'''## 最新：2026-11-14 十条离线预检已批准并封存，当前GUI继续原版

权威`{HERE.name}/experiment-current.json`→`{pub.name}/status.json`及`{name}`。当前11/29终局已封存、0基础设施/cleanup失败；原生审计累计205主/102Flash，最新增10主；旧raw检查保留原时间，非重新全量哈希。实际UID/fullcmd/start/UUID/compute及主17/Flash9锁已核，快照T058正常baseline第19决策。以后调用不混入本审计数字。

用户已明确批准固定10条离线开发：主system唯一已封后缀+292native tokens、最多10次2048输出、原图/完整历史/seed42/greedy/BF16/SDPA；基线复用，0GUI/Flash/scorer/付费API/自动重试。83文件包manifest `{build['manifest_sha256']}`远端已核，原74源码相同；33新CPU资源/锁/前置/输入边界通过仅静态准备，0新模型调用，尚未提交。须当前29全部正常结束、终局seal/链及GUI/main/Flash/launcher实际退出后，再新核归属/UUID/无外来compute/显存并原锁继承，一次离线启动；不得旧launcher/队列/容量/终局重跑。主0–6、7闲置仍保留，成本记8卡。正式新GUI未获批准，无需重问这10条开发。

语义权威`semantic-review-current.json`链接T058旧帧完整配对及T017两个配对：未决不是无Mirage，完整同轨迹或官方评分/全YES不代表降低。Flash仍独立单完整图通用YES/NO，NO持续复拍，主历史不变。效果未证明/降幅null，目标ACTIVE。以下旧头仅历史。

'''
    for p in heads[:3]:
        assert p.read_bytes() == previous[p]
        p.write_bytes(head.encode('utf8') + previous[p])
    assert (HERE / 'experiment-current.json').read_bytes() == previous[HERE / 'experiment-current.json']
    temporary = HERE / ('.experiment-pointer-' + str(ts) + '.json')
    save(temporary, pointer)
    temporary.replace(HERE / 'experiment-current.json')
    save(HERE / 'evidence-discipline-offline-preparation-current.json', {
        'publication': str(pub), 'status': bind(pub / 'status.json'), **status['approved_development']})
    print(json.dumps({'publication': str(pub), 'GUI_terminals': 11, 'new_offline_calls': 0,
                      'submitted': False, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
