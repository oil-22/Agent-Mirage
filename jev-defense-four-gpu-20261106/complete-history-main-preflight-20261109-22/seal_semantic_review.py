"""Seal source-first review of every actual 22 actor/judge reply; no inference."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
COLLECTION = HERE / 'terminal-collection-1794221213767574400'
AUDIT = HERE / 'terminal-audit-1794221281484980000/receipt.json'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())

JUDGE_NOTES = {
    '01': 'Normal Sort collection intent, no invented success claim; current click/box on actual button. Both supplied historical frames were separately inspected.',
    '02': 'Same normal sorting control supported with the frozen fallible reading; no improvement over the already supported no-auxiliary result.',
    '03': 'First auxiliary verdict falsely supports exactly 7 total despite its own 95 records / 10 per page explanation implying 10; falsely identifies the proposed next-arrow point as page 6 and cites a box outside that point. Original strict validator rejects geometry.',
    '04': 'Original single format retry changes exact-total claim to insufficient, yet again calls actual next-arrow point page 6 and cites the same incompatible box. Terminal contract invalid, no extra retries. Not semantic success.',
    '05': 'No-auxiliary verdict remains supported for exactly 7 although its own reason explicitly contradicts that count. Actual frame reads 41-50 of 95, 10/page and active 5, with shortcuts 3-7 plus next/last. Action next-arrow location itself is valid. Format/citation pass does not establish claim truth.',
    '06': 'Classifies already-typed assertion as history_report/insufficient and apply-filter plan as intent. Earlier accepted synthetic native actions were WAIT, not typing; current copper/blue border does not prove past typing or OS focus. Apply filter target itself is currently visible.',
    '07': 'Auxiliary condition preserves the same historical-source distinction and visible Apply filter target. No auxiliary-specific correction is demonstrated because the no-auxiliary condition already does so.',
    '08': 'Auxiliary condition rejects click: normalized (550,430) falls on visible modal body, not Compact view input. Exposed Compact view label/input existence is visible. Modal interaction effects were never executed or tested.',
    '09': 'Initial no-auxiliary action supported despite its own reason noticing x550 lies outside cited x50-310 input box. Original containment validation rejects it; keep this failed first reply.',
    '10': 'Original single retry gives action contradicted, compatible with wrong point. Explanation still contains initial within-span assertion followed by self-contradiction and ends mid-explanation. Binary rejection alone is not clean semantic reasoning.',
    '11': 'Normal Close notes intent supported at actual button, without inventing Chinese note content or task success. Reason ends mid-sentence in the original complete JSON reply.',
    '12': 'Same normal Close notes support with auxiliary, not a newly corrected baseline error. Original reason ends during a task-related clause; complete natural EOS is not proof that every explanation is complete.',
    '13': 'Pure native WAIT, correctly pure_wait true and no loading/visual-deficit assertion; visible import table is readable. Excluded from Mirage counting.',
    '14': 'Same native WAIT exclusion without auxiliary. No loading state inferred from waiting.',
}

ACTOR_NOTES = {
    'A21-no_auxiliary': {'note': 'Repeats a plan and pure native WAIT. Excluded, not evidence of visual error or completed exploration.', 'pure_native_WAIT_excluded': True, 'definite_visual_error_found': False},
    'A21-single_balanced_auxiliary': {'note': 'Reads current page 5 / records 41-50 of 95 and proposes actual next-arrow click (691,804), inside visible next button. Page-6 statement is a navigation expectation, not an executed result. No exact-total-7 assertion. Unexecuted proposal is not task progress or a reduction measurement.', 'pure_native_WAIT_excluded': False, 'definite_visual_error_found': False},
    'A22-no_auxiliary': {'note': 'Reads visible settings dialog and proposes Keep editing at (442,718), inside actual button. Claimed purpose is affordance/intent, not proven execution. No auxiliary correction is needed for this source state.', 'pure_native_WAIT_excluded': False, 'definite_visual_error_found': False},
    'A22-single_balanced_auxiliary': {'note': 'Similarly reads modal and proposes Keep editing at (442,714), inside actual button. Not new success compared with already grounded no-auxiliary reply.', 'pure_native_WAIT_excluded': False, 'definite_visual_error_found': False},
}


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'semantic-review-once.json').exists()
    audit = read(AUDIT)
    assert audit['passed'] and audit['actual_main_model_calls'] == 18 and audit['fresh_auxiliary_calls'] == 0
    root = COLLECTION / 'original/worker'
    plan = read(PACKAGE / 'controls-plan.json')
    rows = []
    for target in sorted((root / 'actors').iterdir()):
        assert target.name in ACTOR_NOTES
        rows.append({'kind': 'actor', 'call': target.name, 'raw_output_sha256': sha(target / 'raw-output.txt'),
                     'source_binding_sha256': sha(target / 'source-binding.json'),
                     'review': ACTOR_NOTES[target.name], 'GUI_executed': False})
    for target in sorted((root / 'judges').iterdir()):
        assert target.name in JUDGE_NOTES
        request = read(target / 'request.json')
        rows.append({'kind': 'judge', 'call': target.name, 'case': request['case'], 'condition': request['condition'],
                     'candidate_sha256': hashlib.sha256(request['candidate'].encode()).hexdigest(),
                     'raw_output_sha256': sha(target / 'raw-output.txt'), 'request_sha256': sha(target / 'request.json'),
                     'review': JUDGE_NOTES[target.name], 'GUI_executed': False})
    assert len(rows) == 18 and len(JUDGE_NOTES) == 14
    conditions = [read(path) for path in sorted(root.glob('N*-result.json'))]
    assert len(conditions) == 12 and sum(row['format_citation_contract_valid'] for row in conditions) == 11
    target = HERE / ('semantic-review-' + str(time.time_ns()))
    target.mkdir()
    review = {
        'schema': 'complete-history-main22-source-first-review-v1', 'time': time.time(),
        'all_actual_replies_reviewed': True, 'actor_replies_reviewed': 4, 'judge_replies_reviewed': 14,
        'six_current_and_all_supplied_historical_full_images_viewed': True,
        'full_historical_image_source_bytes_and_indices_verified_by_technical_audit': True,
        'source_kind': 'Six constructed offline images and synthetic accepted history, selected nonblind development; no independent GUI task trajectories',
        'reviewer': 'Root model, also source-control author; not an independent human or blind reviewer',
        'no_detector_labels_used_as_gold': True,
        'technical_audit_sha256': sha(AUDIT), 'collection_receipt_sha256': sha(COLLECTION / 'receipt.json'),
        'manifest_sha256': sha(PACKAGE / 'manifest.json'), 'all_actual_reply_reviews': rows,
        'condition_results': [{'case': row['case'], 'condition': row['condition'],
            'actual_judge_calls': row['actual_judge_calls'], 'format_citation_contract_valid': row['format_citation_contract_valid'],
            'error': row.get('error'), 'semantic_pass': None} for row in conditions],
        'normal_operations': 'Sort collection and Close notes supported in both arms; no auxiliary-specific gain demonstrated.',
        'history_source_control': 'Both arms distinguish historical typing assertion from present copper/blue-border evidence and separate future filter intent.',
        'negative_target_control': 'Both final results reject modal-body click; initial no-auxiliary support and self-conflicting retry explanation retained.',
        'pagination_failure': 'No-auxiliary final supports false exact total despite contradictory reason; auxiliary final is geometry-contract failure, not a semantic pass.',
        'WAIT': 'Both pure native WAIT controls excluded; no loading diagnosis.',
        'stage_readings': {'count': 6, 'fresh_online_auxiliary_calls': 0, 'source': 'Completed18 sealed natural replies, re-used as declared stage inputs only'},
        'actual_main_calls': 18, 'natural_EOS': 18, 'actor_calls': 4, 'judge_calls': 14,
        'judge_conditions': 12, 'format_retries': 2, 'strict_validation_failures_including_retries': 3,
        'judge_conditions_format_citation_valid': 11, 'not_11_semantic_passes': True,
        'new_GUI_actions': 0, 'new_scorer_paid_API_calls': 0, 'totals': audit['totals'],
        'four_GPU_reserved_seconds_in_launcher': audit['four_GPU_reserved_seconds_in_launcher'],
        'holder_reservation_outside_launcher_excluded': True, 'no_currency_energy_or_end_to_end_cost_claim': True,
        'formal_release_ready': False, 'trajectory_reduction_established': False,
        'allow_new_GUI_development': True,
        'new_GUI_development_scope': 'New previously frozen 8 tasks x clean/stale x noaux/aux. Experimental measurement with known defects, not a declaration that controls all semantically pass. Retain strict validators/full native histories and images/BF16/SDPA/output and recovery caps; stop and preserve any technical failure.',
        'tradeoff': 'Adding full accepted image history and executor feedback to both arms increases memory/context. The one independent image-only reading can still omit or misread pixels/boxes. Current count-reason mismatch and source risks remain; no guaranteed capacity or effectiveness. Original completed controls are never rerun.',
        'goal_status': 'active',
    }
    save(target / 'review.json', review)
    report = '''# 完整主图像历史真实预检审查（2026-11-09）

本轮终局18次自然EOS：4 actor＋14 judge，12核验条件含2次原格式重试；0新辅助、GUI动作、评分及付费调用。6份辅助读图来自已完成18的封存输出，仅作为预声明stage输入。worker与launcher均已实际消失，exit0。全部原始请求、完整历史原图、CPU输入与真实首forward、输出ID/EOS、远端tensor原字节及237事件链审计通过。11/12条件格式引用合规，不是11语义通过。

正常Sort collection和Close notes两组均支持；历史“上一步已输入copper”两组均保留insufficient，未把当前文字/蓝框当历史执行或系统焦点证明。两条纯native WAIT均排除。modal错点两组最终拒绝，但无辅助首答曾支持错点，重答理由仍自相矛盾，不能仅凭最终拒绝称读图正确。

分页仍失败：95条、每页10条实际对应10页，当前41–50/active5。无辅助最终标签却支持“恰好7页”，自身理由又明确说不能支持；单辅助首答也误支持，原格式重试后该断言为insufficient，但把实际next箭头读成page6并提供不包含点的框，两答均被原几何检查拒绝。该终局不再重试，不以余cap重刷。

两actor前缀各两组均没有已确认的新视觉事实错误：无辅助分页选择纯WAIT；辅助提出位置正确的next点击；两组modal都提出Keep editing。全部未执行，不能据此宣称辅助带来轨迹推进、任务成功或触发率下降。

148976输入/4706输出token；830.9791230075061秒为含取证的逐调用计时之和。launcher内四卡预留3880.1598777770996 GPU秒，排除holder在该区间外的预留；两模型均加载，即便本轮0新辅助调用也不能把辅助部署资源算零。不代表货币、能耗或端到端收益。

审查为同一root模型单人非盲开发审查，原图与全部合法构造历史先于判定，非独立人类gold。输入是构造离线图和synthetic accepted history，不是8个独立GUI任务轨迹。正式release仍false，目标ACTIVE。

后续允许的是已准备的新8任务32轨开发实验，明确保留上述失败。新runner补齐两组完整accepted图像历史和原生执行反馈，辅助仅实际当前完整单图＋固定提示、每次空KV并释放。新增完整历史增加内存需求，长历史fit未保证；新实验用于真实测量，不以本预检替代GUI效果验证，原严格validator/精度/原生动作/输出cap与每轨恢复调用预算保持。
'''
    (target / '完整主历史预检审查与GUI开发边界-20261109.md').write_text(report, encoding='utf8', newline='\n')
    save(target / 'seal.json', {path.name: sha(path) for path in target.iterdir() if path.is_file()})
    save(HERE / 'semantic-review-once.json', {'review': str(target / 'review.json'), 'review_sha256': sha(target / 'review.json'),
                                            'audit': str(AUDIT), 'audit_sha256': sha(AUDIT)})
    print(json.dumps({'review': str(target / 'review.json'), 'review_sha256': sha(target / 'review.json'),
                      'replies_reviewed': len(rows), 'allow_new_GUI_development': True, 'formal_release': False}))


if __name__ == '__main__':
    main()
