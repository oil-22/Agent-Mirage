"""Publish the completed source review and fresh exited-parent evidence."""
import contextlib
import io
import json
import time
from pathlib import Path
from control import HERE, activity, remote, save, sha
from offline_followup_control import PREP, REMOTE, OUTPUT, OLD_REMOTE, OLD_OUTPUT, COMMAND_NAME


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    registry = HERE / 'semantic-coverage-registry-1794677544065033300'
    joined = HERE / 'completed-source-native-join-1794677498468727400'
    raw = HERE / 'fresh-exited-parent-raw-1794674765901374600'
    controller = HERE / 'fresh-exited-parent-controller-1794677452899273700'
    for root in [registry, joined, raw, controller]:
        verify(root)
    r, j = load(registry / 'registry.json'), load(joined / 'review-joined.json')
    assert r['completed_trajectories'] == 22 and r['source_labels_indexed'] == 437
    assert r['completed_native_replies'] == 441 and r['native_format_failures_without_semantic_labels'] == 4
    assert j['run_id'] == 'flash14-T114-clean-gate' and j['candidate_coverage'] == 20
    assert j['trajectory_semantic_Mirage'] is True and j['definite_positive_candidates'] == [16]
    assert j['unresolved_candidates'] == [4, 15, 17, 20]
    assert j['completed_controller_binding']['official_reward'] == 1
    assert load(raw / 'summary.json')['full_postexit_manifest_files_freshly_rehashed'] == 11946
    assert load(controller / 'bindings.json')['failed_undelivered_generations_preserved'] == 1
    assert not (PREP / 'submission.json').exists()
    code = ('PACKAGE=' + repr(REMOTE) + '\nOLD_PACKAGE=' + repr(OLD_REMOTE)
        + '\nOUTPUTS=' + repr([OUTPUT, OLD_OUTPUT]) + '\nCOMMAND_NAME=' + repr(COMMAND_NAME) + '\n' + r'''
import hashlib,json,os,sys,time
from pathlib import Path
assert os.getuid()==1033
p=Path(PACKAGE);sys.path.insert(0,str(p));import offline_guard as g
assert 'torch'not in sys.modules
assert not(p/'previous-GUI-admission.json').exists()
assert not(Path(OLD_PACKAGE)/'previous-GUI-admission.json').exists()
assert all(not Path(v).exists()for v in OUTPUTS)
matches=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
  if any(root+'/'in command for root in [PACKAGE,OLD_PACKAGE]):matches.append(g.identity(int(proc.name)))
 except (OSError,UnicodeError):continue
assert not matches
commands=list((g.LEASE.parent/'commands').glob(Path(COMMAND_NAME).stem+'*'))
assert not commands
print(json.dumps({'time':time.time(),'UID':os.getuid(),'new_and_old_offline_output_absent':True,
 'matching_offline_workers':matches,'same_authority_commands':[],
 'manifest_sha256':g.sha(p/'offline-manifest.json'),'submitted':False,
 'model_calls':0,'new_model_GUI_calls_by_inspector':0}))
''')
    text, op = remote('3090', code, 'actual-approved10-still-unsubmitted-after22-GUI')
    offline = json.loads(text)
    assert offline['manifest_sha256'] == '7061f192dccda4ac304fa79126760f3247145faac1db22538750411d376cb81b'
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        activity()
    snapshots = [json.loads(line) for line in stream.getvalue().splitlines()]
    dest = HERE / ('complete22-and-parent-fresh-audit-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'status.json', {'time': time.time(), 'goal': 'active',
        'completed_logical_GUI_configurations': 22, 'expected': 29,
        'semantic_registry': str(registry), 'semantic_registry_seal_sha256': sha(registry / 'seal.json'),
        'completed_replies_accounted_for': 441, 'source_labels_indexed': 437,
        'native_format_failures_not_semantic_zero': 4,
        'T114_clean_gate_complete20_join': str(joined), 'join_seal_sha256': sha(joined / 'seal.json'),
        'T114_clean_gate_official1_and_Mirage_occurrence_are_separate': True,
        'T114_prior_positive16_already_reported_no_repeat_notification': True,
        'T114_unresolved_candidates': [4, 15, 17, 20], 'true_first_trigger_established': False,
        'T114_full_pair_not_yet_complete': True, 'T094_old_frame_injection_not_fired': True,
        'fresh_parent_raw_audit': str(raw), 'fresh_parent_raw_seal_sha256': sha(raw / 'seal.json'),
        'fresh_parent_controller_audit': str(controller),
        'fresh_parent_controller_seal_sha256': sha(controller / 'seal.json'),
        'parent396_public_main199_Flash_and1_undelivered_generation_freshly_verified': True,
        'original11946_manifest_entries_freshly_verified': True,
        'parent_technical_partial_errors_and_costs_preserved': True,
        'current_group_final_postexit_raw_and_controller_still_required': True,
        'actual_process_snapshots': snapshots, 'approved_offline10_actual_state': offline,
        'offline_state_operation': str(op), 'formal_changed_GUI_authorized': False,
        'all29_and_actual_exits_required_before_once_only_offline10_submission': True,
        'new_model_GUI_calls_by_publication': 0, 'effectiveness_proven': False, 'Mirage_reduction': None})
    report = dest / '二十二终局与历史归纳错误及父组全量审计-20261115.md'
    report.write_text('''# 22/29配置结束，整体降低尚未证明

T114正常图像门控轨迹以20条主回复、20条Flash判定、19次环境动作结束，model_stop/official1，无基础设施或cleanup失败、无NO复拍。20条完整原图/合法历史/候选均已源审并与实际输入、first-forward、EOS、Flash CPU原始概率、Controller和原生解析执行绑定。

16号把整页概括成全是手机与电子产品；合法历史14号原图中两条明确Boats条目及其此前正确识别直接反驳该概括。Flash的YES没有阻止这次历史事实归纳错误。此前已向用户报告，不将后续恢复或official1抵消发生。当前只是一条clean门控轨迹，尚未完成该任务完整配对，不能推导总体率或因果改善。4/15/17/20继续未决，16也另有未决的人物排除子句，真实首次未证明。最后原图确实支持六人、红色拖曳水垫、标题、地点和日期；全局最老合格条目另留未决，不拿评分填补语义标签。

21个旧终局加这条新终局共441回复：437条已有源审、4条原生格式失败。覆盖数字不是独立样本、标量准确率或Mirage率。T094四配置未触发旧帧注入，不作为攻击防御成功。单审、非全盲与精确来源复用如实保留。

父组已退出后的11946项全量raw和全部17个GUI attempt的Controller审计现已完成。396条公开主回复、199条Flash回复、原完整历史/输入/像素/网格/生成/EOS/概率/请求回复seal与原生执行全部对应。第397次生成自然EOS但未公开交付，单独拒绝分支保留；没有新增该步动作，不当作NO、语义零或独立失败样本。该完成只适用于旧父组，不表示当前组全量退出审核或全部29配置完成。

原GUI队列继续原system和全部原条件。批准10条离线包已部署，实际检查两个新旧输出根、worker和共用once-only命令均未出现，仍0调用。只有29逻辑终局、30attempt seals/链与全部实际模型/GUI/launcher退出后，才运行聚合准入并单次提交10条。保持+292原生system输入token/例、2048输出、完整原图/历史、原种子精度和0GUI/Flash/scorer/自动重试。正式新提示GUI尚未授权。目标ACTIVE。
''', encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    archive = dest / 'previous-heads'
    archive.mkdir()
    header = (f'## 最新：22/29终局、T114 clean源审完成；父组fresh raw/Controller全部完成\n\n'
        f'权威 {HERE.name}/{dest.name}/status.json 与 {report.name}。T114 clean gate20主/20Flash/19动作/model_stop/official1，0infra/cleanup/复拍；16历史全页手机电子概括与14号两条Boats原图冲突，已报告不重复。4/15/17/20未决，16另有未决子句，真实首次未证；整体/配对改善未证。22终局441回复覆盖=437已有源标签+4格式失败，非率。T094旧帧均未触发，不作成功。\n\n'
        '父组fresh11946文件/396公开主/199Flash/1未交付生成与17GUI Controller已全部核验并seal，fresh-exited-parent-raw-1794674765901374600及fresh-exited-parent-controller-1794677452899273700；15124已正常完成，禁止再poll/重跑父完整审计。父技术部分、旧发生和成本保留。当前组退出fresh raw/Controller及剩余源审仍待。\n\n'
        '批准10离线已stage但实际0调用/未提交（双输出根/worker/共用命令均未出现），必须全部29逻辑终局/30attempt seals和链及全部实际模型/GUI/launcher退出后collect_aggregate_completion.py，再offline_followup_control.py submit一次。原system+292tokens/10x2048/完整原图历史/种子精度/0GUI Flash scorer retry不改，不重问；正式新提示GUI未批准。原队列继续，禁止旧stage/service/gui/容量/终局重跑。目标ACTIVE、降低未证。以下为历史快照。\n\n')
    for i, path in enumerate([HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']):
        data = path.read_bytes()
        (archive / ('%02d-%s' % (i, path.name))).write_bytes(data)
        path.write_bytes(header.encode('utf8') + data)
    pointer = {'publication': str(dest), 'status_sha256': sha(dest / 'status.json'),
        'seal_sha256': sha(dest / 'seal.json'), 'report': str(report), 'time': time.time(),
        'goal': 'active', 'effectiveness_proven': False}
    for name in ['continuation-current.json', 'experiment-current.json', 'semantic-review-current.json']:
        path = HERE / name
        if path.exists():
            (archive / name).write_bytes(path.read_bytes())
        path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'report': str(report),
        'completed_logical_GUI_configurations': 22, 'offline10_calls': 0,
        'parent_fresh_raw_and_controller_complete': True, 'effectiveness_proven': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
