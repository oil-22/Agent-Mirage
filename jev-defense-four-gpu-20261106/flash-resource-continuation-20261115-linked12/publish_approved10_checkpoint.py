"""Publish immutable progress and preserve preceding mutable handoff heads."""
import contextlib
import io
import json
import time
from pathlib import Path
from control import HERE, activity, save, sha
from offline_followup_control import PREP

NATIVE = HERE / 'live-evidence-incremental-1794675175469556900'
CPU = HERE / 'Flash-CPU-increment-1794675175907872300'
REVIEW = HERE / 'exact-source-prefix-reuse-1794675209503155400'
BINDING = HERE / 'source-native-prefix-binding-1794675255578152700'
PARENT_RAW = HERE / 'fresh-exited-parent-raw-1794674765901374600'


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    for root in [NATIVE, CPU, REVIEW, BINDING]:
        assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    native, cpu, review = load(NATIVE / 'summary.json'), load(CPU / 'cumulative-report.json')['result'], load(REVIEW / 'review.json')
    assert native['cumulative_verified_main_replies'] == 34
    assert cpu['verified_complete_Flash_replies'] == 34
    assert review['candidate_coverage'] == load(BINDING / 'binding.json')['candidate_coverage'] == 34
    assert not (PREP / 'submission.json').exists()
    assert load(PREP / 'stage-receipt.json')['result']['worker_submitted'] is False
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        activity()
    rows = [json.loads(s) for s in stream.getvalue().splitlines()]
    actual = {v['host']: v for v in rows}
    primary = actual['3090']['data']
    gui = actual['4090']['data']
    assert all(primary[k]['same_live'] for k in ['launcher_actual', 'main_actual', 'Flash_actual'])
    assert gui['GUI_actual']['same_live']
    assert not any(k in primary for k in ['primary/failure.json', 'launcher-failure.json', 'exit.json'])
    dest = HERE / ('approved10-and-source34-checkpoint-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    state = {'time': time.time(), 'goal': 'active', 'original_GUI_logical_configurations': 29,
        'parent_noninfrastructure_terminals': 16, 'parent_native_contract_failures_within16': 4,
        'parent_technical_attempts_preserved_separately': 1,
        'continuation_expected': 13, 'current_actual_GUI_status': gui['batch/status.json'],
        'actual_process_receipts': {h: v['receipt'] for h, v in actual.items()},
        'actual_primary_status': primary['primary/status.json'],
        'native_audit': str(NATIVE), 'native_audit_seal_sha256': sha(NATIVE / 'seal.json'),
        'cumulative_new_root_main_raw_verified': 34, 'cumulative_new_root_Flash_raw_verified': 34,
        'old_raw_check_times_retained_not_fresh_full_rehash': True,
        'Flash_CPU_audit': str(CPU), 'Flash_CPU_seal_sha256': sha(CPU / 'seal.json'),
        'Flash_CPU_replies_verified': 34, 'actual_held_primary_and_Flash_locks': [17, 9],
        'source_review': str(REVIEW), 'source_review_seal_sha256': sha(REVIEW / 'seal.json'),
        'native_source_binding': str(BINDING), 'native_source_binding_seal_sha256': sha(BINDING / 'seal.json'),
        'source_prefix_coverage': 34, 'source_prefix_partial_only': True,
        'source_labels_reused_after_exact_full_input_original_PNG_and_reply_equality': True,
        'new_independent_reviewer_count': 0, 'previously_reported_positive_not_a_new_finding': [15],
        'unresolved_candidates': [4], 'true_first_trigger_not_proven': True,
        'offline10_preparation': str(PREP),
        'offline10_manifest_sha256': sha(PREP / 'package/offline-manifest.json'),
        'offline10_staged_without_submit': True, 'offline10_new_calls': 0,
        'offline10_pending_real_state_gate_check': str(PREP / 'pending-gate-check.json'),
        'offline10_pending_gate_check_sha256': sha(PREP / 'pending-gate-check.json'),
        'offline10_same_approved_plan_sha256': '98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a',
        'offline10_all85_payload_files_identical_to_first_aggregate_preparation': True,
        'offline10_one_shared_command_prevents_old_and_new_path_double_budget': True,
        'original_83_file_preparation_and_first_aggregate_manifest_preserved': True,
        'offline10_actual_positive_all29_admission_not_satisfied': True,
        'formal_changed_GUI_authorized': False,
        'parent_fresh_raw_audit': {'root': str(PARENT_RAW), 'complete': (PARENT_RAW / 'seal.json').exists(),
            'main_request_checkpoint_files_saved': len(list(PARENT_RAW.glob('main-*.json'))),
            'running_local_exec_session': 15124,
            'resumption_if_session_lost': 'audit_exited_group_raw.py --group parent --resume ' + str(PARENT_RAW),
            'parent_11946_fresh_full_success_not_claimed_until_final_seal': True},
        'runtime_sources_conditions_and_budgets_unchanged': True,
        'eight_reserved_GPUs_for_deployment_cost': True, 'effectiveness_proven': False, 'Mirage_reduction': None}
    save(dest / 'status.json', state)
    report = dest / '十条授权预检部署与GUI续跑检查-20261115.md'
    report.write_text('''# 十条离线预检已部署，GUI继续原版

用户批准已落实，未重复询问。原10个输入、system后缀增加292原生token、完整原图与合法历史、BF16/SDPA、seed42 greedy、2048输出和最多10次调用保持；基线回复复用，0新增Flash/GUI/评分/付费API/自动重试。正式修改主提示的GUI尚未授权。

85文件聚合准入包已实际放到3090，但尚未提交模型命令、尚无离线新结果。新的不可变准备只纠正前一聚合manifest残留的远端目录描述，全部85个实际payload字节相同。原83文件包和首个聚合准备均保留，两个路径共用原once-only命令名，不能各花10次。12项纯逻辑覆盖边界检查引用原时；实际运行状态下的负向准入也确认拒绝：未完成的GUI没有terminal文件，不可开离线实验。检查器先前只预期AssertionError造成的报告失败已保全，只修复本地检查器对这个特定缺失文件的记录，原guard不改、0模型调用。

GUI仍是父16个非基础设施终局（含4个原生格式失败）＋新13个剩余配置；父T089技术中断部分、旧错误和成本均保留。当前真实步数见status.json所列两机回执；原生增量已核34主、34Flash及34个实际动作，Flash原始tensor/readout概率CPU累计34。主17/Flash9继承锁及实际UID/full command/start/UUID/compute均核验，主0–6＋Flash7计8卡。

新根前34个完整输入、全部合法历史、原PNG和候选与原T089基线已审来源精确相同，透明复用同一审查，不创造独立审查者；来源标签在实际native/CPU/parser/action join前封存。已有15号阳性不是新发现，4号保持未决，部分轨迹不能当整轨无Mirage或配对效果，真实首次仍未证。旧source审查和终局均不重跑、不改。

已退出父根的完整原始文件新鲜审计另在进行，检查点、实际原进程退出和11946项原postexit清单身份已绑定。审计尚未封存前不声称全量新鲜复核通过；后续还需新根退出后的全量raw及完整Controller跨机绑定。

只有父16＋新13精确覆盖原29、所有30个attempt终局/文件seal/链完整、相关模型/GUI/launcher实际退出后，才运行collect_aggregate_completion.py取得聚合准入，再一次offline_followup_control.py submit。禁止原单根29 submit、旧队列、已完成容量、服务或终局重跑。当前整体降低Mirage尚未证明，目标ACTIVE。
''', encoding='utf8')
    save(dest / 'receipt.json', {'status_sha256': sha(dest / 'status.json'),
        'report_sha256': sha(report), 'runtime_sources_changed': False,
        'new_model_calls_by_publication': 0, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    targets = [HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']
    archive = dest / 'previous-heads'
    archive.mkdir()
    header = (f'## 最新：GUI续跑、34源回复已审绑定；授权10条已部署但未提交\n\n'
        f'权威 {HERE.name}/{dest.name}/status.json 与 {report.name}。原生/CPU累计34主、34Flash，实际主17/Flash9锁与UID/fullcmd/start/UUID/compute核验；新根T089前34完整body/合法历史/原PNG/候选与已审来源精确相同，透明复用非新增审查者，原阳性15已报告、4未决，部分轨迹非配对效果。原父16非基础设施终局内4个native格式失败、1技术中断另保留，新13续跑原版，旧错误成本不清零。\n\n'
        '批准10条新85包已stage，manifest7061f192dccda4ac304fa79126760f3247145faac1db22538750411d376cb81b，0调用/未提交；原plan98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a/10完整body/+292输入token/2048/原种子与预算不变。旧83包/首个聚合包保留且共用一个once-only命令预算。实际GUI未完成时拒绝准入已核；纯cover12引用原时，不称真实29完成。只有两根全部29逻辑终局、30attempt seals/链和全部实际退出后 collect_aggregate_completion.py，再 offline_followup_control.py submit 一次。不重问，不用旧单根submit、不重启stage/service/gui/holder/容量/旧终局。正式改版GUI尚未批准。\n\n'
        f'父根11946项fresh raw审计正在 {PARENT_RAW.name}，本地exec15124；尚未最终seal，不能称全量通过。失联先检查已存证据再原源码--resume，不重跑已完成。所有新旧最终raw/Controller/语义审查仍待。目标ACTIVE，降低未证。以下running/stopped为旧时快照。\n\n')
    archived = {}
    for index, path in enumerate(targets):
        previous = path.read_bytes() if path.exists() else b''
        name = '%02d-%s' % (index, path.name)
        (archive / name).write_bytes(previous)
        archived[str(path)] = {'copy': name, 'sha256': sha(archive / name)}
        path.write_bytes(header.encode('utf8') + previous)
    save(archive / 'manifest.json', archived)
    pointer = {'publication': str(dest), 'status_sha256': sha(dest / 'status.json'),
        'seal_sha256': sha(dest / 'seal.json'), 'goal': 'active', 'effectiveness_proven': False, 'time': time.time()}
    for name in ['experiment-current.json', 'continuation-current.json']:
        path = HERE / name
        if path.exists():
            (archive / name).write_bytes(path.read_bytes())
        path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'GUI_status': gui['batch/status.json'],
         'offline10_staged': True, 'offline10_calls': 0, 'parent_raw_audit_complete': state['parent_fresh_raw_audit']['complete'],
         'effectiveness_proven': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
