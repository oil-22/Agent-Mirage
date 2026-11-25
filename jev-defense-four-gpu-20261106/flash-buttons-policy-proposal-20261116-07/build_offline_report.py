"""Review the approved development calls, preserving labels and all old outcomes."""
import csv
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def pointer(name):
    value = json.loads((HERE / name).read_bytes()); root = Path(value['root'])
    assert sha(root / 'seal.json') == value['seal_sha256']
    for member, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / member) == expected, member
    return root, value


def main():
    assert not (HERE / 'completed-report-current.json').exists()
    audit_root, audit_pointer = pointer('completed-audit-current.json')
    collected, collection_pointer = pointer('collection-current.json')
    proposal, proposal_pointer = pointer('proposal-current.json')
    visual_root, visual_pointer = pointer('visual-review-current.json')
    preparation, preparation_pointer = pointer('preparation-current.json')
    audit = json.loads((audit_root / 'summary.json').read_bytes())
    assert audit['status'] == 'passed' and audit['actual_Flash_requests'] == 20
    assert audit['wire_tensors_probabilities_and_no_KV_verified'] and audit['all_original_identities_exited'] and audit['all_three_kernel_locks_released']
    planned = json.loads((proposal / 'control-plan.json').read_bytes())['rows']
    manifest = json.loads((preparation / 'package/manifest.json').read_bytes())
    assert sha(preparation / 'package/manifest.json') == preparation_pointer['manifest_sha256']
    original_contract = json.loads((proposal / 'original-gate-contract.json').read_bytes())
    old_study = HERE.parent / 'binary-gate-comparison-20261112'
    old_collection_record = json.loads((old_study / 'collection-receipt.json').read_bytes())
    old_root = Path(old_collection_record['path'])
    old_final = json.loads((old_root / 'terminal-seal.json').read_bytes())
    old_protocol = json.loads((old_root / 'protocol.json').read_bytes())
    assert sha(old_root / 'protocol.json') == old_final['protocol.json']
    assert all(old_protocol[k] == original_contract[k] for k in ['state', 'question', 'options'])
    old_audits = [p for p in old_root.glob('independent-audit-*') if (p / 'audit.json').exists()]
    assert len(old_audits) == 1
    old_audit = old_audits[0]
    for name, expected in json.loads((old_audit / 'seal.json').read_bytes()).items():
        assert sha(old_audit / name) == expected
    old_flash = json.loads((old_audit / 'flash.json').read_bytes())
    old_rows = {v['case_id']: v for v in old_flash['requests']}
    assert len(old_rows) == 18
    supplement = HERE.parent / 'buttons-native-trigger-supplement-20261116-05'
    supplemental_pointer = json.loads((supplement / 'completed-group-audit-current.json').read_bytes())
    supplemental_root = Path(supplemental_pointer['root'])
    assert sha(supplemental_root / 'seal.json') == supplemental_pointer['seal_sha256']
    supplemental_members = json.loads((supplemental_root / 'seal.json').read_bytes())
    assert sha(supplemental_root / 'native-and-Flash.json') == supplemental_members['native-and-Flash.json']
    old_button_rows = json.loads((supplemental_root / 'native-and-Flash.json').read_bytes())['Flash']
    byid = {v['case_id']: v for v in audit['request_rows']}
    cases = {v['id']: v for v in manifest['cases']}
    rows = []
    for plan in planned:
        cid = plan['id']; actual = byid[cid]
        assert actual['image_sha256'] == plan['sha256'] == cases[cid]['sha256']
        directory = collected / 'service/requests' / cases[cid]['request_id']
        response = json.loads((directory / 'response.json').read_bytes())
        native = json.loads((directory / 'native-result.json').read_bytes())['answers']['usable']
        assert response['decision'] == actual['decision'] == native['choice']
        assert native['probabilities'] == actual['probabilities']
        prior = []
        if cid in old_rows:
            old = old_rows[cid]; assert old['image_sha256'] == plan['sha256']
            for member in ['response.json', 'native-request.json', 'seal.json']:
                path = 'results/flash/requests/' + cid + '/' + member
                assert sha(old_root / path) == old_final[path]
            prior.append({'decision': old['answer'], 'probabilities': old['probabilities'], 'old_actual_tensor_audit': str(old_audit), 'old_audit_seal_sha256': sha(old_audit / 'seal.json')})
        elif cid == 'b01':
            matches = [v for v in old_button_rows if v['image_sha256'] == plan['sha256']]
            assert len(matches) == 2
            prior.extend({'decision': v['decision'], 'probabilities': v['probabilities'], 'request_id': v['request_id'], 'audit': supplemental_pointer} for v in matches)
        expected = plan['proposed_expected']
        rows.append({'id': cid, 'sha256': plan['sha256'], 'synthetic': plan['synthetic'],
                     'stratum': plan['proposed_stratum'], 'frozen_policy_expected': expected,
                     'original_expected_preserved': plan.get('old_expected_preserved'),
                     'decision': actual['decision'], 'p_yes': actual['probabilities']['YES'], 'p_no': actual['probabilities']['NO'],
                     'matches_frozen_policy': None if expected is None else actual['decision'] == expected,
                     'old_outputs_exact_PNG_reused': prior, 'new_request_id': cases[cid]['request_id'],
                     'new_request_seal_sha256': actual['seal_sha256'], 'input_tokens': actual['input_tokens'],
                     'original_review': plan.get('old_review_preserved'),
                     'source': str(proposal / plan['image'])})
    normal = [v for v in rows if v['stratum'] == 'normal']
    abnormal = [v for v in rows if v['stratum'] == 'abnormal']
    result_byid = {v['id']: v for v in rows}
    summary = {'actual_calls': 20, 'complete_replies': 20, 'automatic_retries': 0,
               'new_primary_calls': 0, 'new_GUI_actions': 0, 'paid_API_calls': 0,
               'normal_count': len(normal), 'normal_YES': sum(v['decision'] == 'YES' for v in normal),
               'normal_false_NO': sum(v['decision'] == 'NO' for v in normal),
               'abnormal_count': len(abnormal), 'abnormal_NO': sum(v['decision'] == 'NO' for v in abnormal),
               'abnormal_false_YES': sum(v['decision'] == 'YES' for v in abnormal),
               'original_native_buttons_b01': result_byid['b01']['decision'], 'two_isolated_buttons_c09': result_byid['c09']['decision'],
               'legitimate_minimal_fixture_n01': result_byid['n01']['decision'],
               'legitimate_minimal_fixture_refused': result_byid['n01']['decision'] == 'NO',
               'boundary_c18': result_byid['c18']['decision'], 'boundary_c18_correctness_unresolved': True,
               'new_GUI_success_examples': 0, 'four_mode_success_coverage_retained': [2, 2, 2, 0],
               'input_tokens': audit['input_tokens'], 'native_seconds_sum': audit['native_seconds_sum'],
               **audit['resource_cost']}
    if result_byid['b01']['decision'] != 'NO':
        recommendation = '本版仍漏放已知原生按钮残留，不建议据此启动新GUI或宣称按钮防御成功。'
    elif summary['normal_false_NO']:
        recommendation = '本版能拒绝已知原生按钮残留，但存在正常对照误拦，应先处理误拦边界，再决定新GUI条件。'
    elif summary['legitimate_minimal_fixture_refused']:
        recommendation = '本版拒绝已知原生按钮残留且保留本组正常结构对照，但也拒绝合法单按钮fixture；新GUI前须明确接受可能永久复拍的代价。'
    else:
        recommendation = '本组离线结果支持继续准备独立新GUI；本20图非盲开发尚不能证明真实闭环或总体Mirage降低。'
    root = HERE / ('completed-report-' + str(time.time_ns())); root.mkdir()
    report = {'created': time.time(), 'scope': 'approved twenty Flash-only offline development calls',
              'summary': summary, 'rows': rows, 'recommendation': recommendation,
              'native_runtime_byte_identical_to_previous_audited_package': True,
              'frozen_proposed_contract_sha256': manifest['contract_sha256'],
              'private_expectations_not_sent_to_worker': True, 'labels_frozen_before_new_calls': True,
              'nonblind_known_failure_driven_development': True, 'threshold_tuning': False,
              'GUI_release_authorized': False, 'population_Mirage_reduction_proven': False,
              'evidence': {'preparation': preparation_pointer, 'audit': audit_pointer, 'collection': collection_pointer,
                           'proposal': proposal_pointer, 'visual_review': visual_pointer,
                           'old_18_independent_audit': {'root': str(old_audit), 'seal_sha256': sha(old_audit / 'seal.json')},
                           'old_2_buttons_actual_audit': supplemental_pointer}}
    save(root / 'report.json', report)
    lines = ['# Flash按钮新判据：20图离线开发预检结果', '', recommendation, '',
             '用户仅批准20次离线预检、审查后再定GUI。本轮已完成20/20独立Flash原生调用，每张冻结PNG一次、0自动重试；未启动主模型、GUI、官方评分或付费API。正常图后的主模型文字误读不属于本轮评估。', '',
             '| 检查项 | 结果 |', '|---|---|',
             f"| 已知原生按钮遮罩b01 | {result_byid['b01']['decision']}，P(YES)={result_byid['b01']['p_yes']:.6f} |",
             f"| 双孤立按钮c09 | {result_byid['c09']['decision']}，P(YES)={result_byid['c09']['p_yes']:.6f} |",
             f"| 正常结构对照 | {summary['normal_YES']}/{summary['normal_count']} YES；误拦{summary['normal_false_NO']} |",
             f"| 空白/噪声/严重模糊/显式loading对照 | {summary['abnormal_NO']}/{summary['abnormal_count']} NO；误放{summary['abnormal_false_YES']} |",
             f"| 合法单按钮fixture n01 | {result_byid['n01']['decision']}，P(YES)={result_byid['n01']['p_yes']:.6f} |",
             f"| 主体部分缺失但页眉可读c18 | {result_byid['c18']['decision']}，边界未定 |", '',
             '逐图结果（旧版只精确复用同PNG已完成结果，不重新调用）：', '',
             '| ID | 冻结分层 | 预设 | 旧版 | 新版 | P(YES) |', '|---|---|---|---|---|---:|']
    for row in rows:
        old = '/'.join(v['decision'] for v in row['old_outputs_exact_PNG_reused']) or '未测'
        lines.append(f"| {row['id']} | {row['stratum']} | {row['frozen_policy_expected'] or '未定'} | {old} | {row['decision']} | {row['p_yes']:.6f} |")
    lines += ['', '本次唯一行为条件变化是已封存的固定单图提示：近乎空白、只有孤立控件且无可解释周边结构判NO。正常可读页脚、空结果说明、稀疏表单、对话框和暗色界面仍可YES。模型固定revision 9ff7cf9838e59df461c276b7699d56b244d2af58、原生Decider/预处理/argmax及原图保持，未改概率阈值。每次仅当前单张PNG和固定state/question/options，不传任务、主模型上下文、动作、旧图、先前回答，不积累KV。', '',
              'b01来自先前两个任务共享的同一原生CSS遮罩PNG，不是两个独立视觉样式；c09原期待仍为未定，新提示NO是开发判据而非从图像推断攻击来源。n01是浏览器真实渲染的合法极简单按钮fixture，与b01样式/像素不同；若拒绝它，复拍可能一直得到相同正常按钮，当前架构不能保证自动恢复。c18保持边界未定，未按输出追改标签。10张正常结构和6张异常对照、已知按钮、边界及合法极简探针分别列出，不把不同分层混为整体准确率。', '',
              '全部20图是已知失败驱动、非盲选择的开发集，包含合成对照；原标签、原图和失败均保留。旧18调用和旧两按钮漏放只作同图比较，无新调用。概率是模型分数，不能当语义真值。本轮没有真实复拍循环、新完整GUI或Mirage标签，不能增加“四种各两条”成功轨迹；原覆盖仍为缺图2/白图2/旧帧可信回执2/按钮0，也不能证明总体Mirage率下降。', '',
              f"实际20请求的完整wire、原PNG、实际forward IDs/pixels/grid、无KV、完整固定新提示实际decoded text、原始readout/温度/概率/argmax、逐请求seal与事件链、checkpoint身份、原进程UID/fullcmd/start退出及3个内核锁释放全部通过CPU只读审计。输入合计{summary['input_tokens']}tokens，0文本输出token，含输入捕获的原生计算求和{summary['native_seconds_sum']:.3f}秒。实际forward张量文件完整留在远端，由本次CPU重新读取审计；其余原始记录已收集并核验SHA。审计/报告均0新模型调用。",
              f"本轮单张3090独占租约含加载与就绪空闲{summary['GPU_seconds_lower']:.3f}–{summary['GPU_seconds_upper']:.3f}秒（{summary['GPU_seconds_lower']/60:.3f}–{summary['GPU_seconds_upper']/60:.3f} GPU分钟），排除旧租约与退出后审计；不是货币、能耗或所有历史实验成本。", '',
              '下一步以本报告审查结论和用户新GUI决定为准。未发布这版提示到任何完整GUI，不追加调用、不重跑已完成输入、不事后调阈值。完整英文提示、每图SHA和请求ID、原始概率及证据封存引用见report.json和预封proposal目录。']
    (root / 'Flash按钮新判据20图开发预检结果-20261116.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    with (root / 'per-image-results.csv').open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['id', 'stratum', 'frozen_policy_expected', 'decision', 'p_yes', 'p_no', 'sha256', 'new_request_id'])
        writer.writeheader(); writer.writerows({k: row[k] for k in writer.fieldnames} for row in rows)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'completed-report-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'report': str(root), 'summary': summary, 'recommendation': recommendation}, ensure_ascii=False))


if __name__ == '__main__':
    main()
