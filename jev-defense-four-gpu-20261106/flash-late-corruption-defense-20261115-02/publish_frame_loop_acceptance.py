"""Publish the human's explicit frame-gate/recapture-loop acceptance result."""
import collections
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    pointer = HERE/'frame-loop-acceptance-current.json'
    assert not pointer.exists() and not (HERE/'completed-publication-current.json').exists()
    audit, ar = checked(HERE/'completed-group-audit-current.json')
    summary = json.loads((ar/'summary.json').read_bytes())
    assert summary['processed_GUI_trajectories'] == 12
    assert summary['all_original_model_GUI_launcher_identities_exited']
    source, sr = checked(HERE/'frame-loop-source-evidence-current.json')
    evidence = json.loads((sr/'evidence.json').read_bytes())
    assert evidence['audit'] == audit
    visual, vr = checked(HERE/'frame-loop-visuals-current.json')
    visual_file = vr/'Flash拦截与复拍闭环实例.png'
    manual_file = HERE/'frame-loop-manual-image-review.json'
    manual = json.loads(manual_file.read_bytes())
    assert manual['source_evidence'] == source
    cases = evidence['cases']
    assert len(cases) == 4
    assert {r['run_id'] for r in manual['cases']} == {r['run_id'] for r in cases}
    for case in cases:
        label = next(r for r in manual['cases'] if r['run_id'] == case['run_id'])
        expected = {d[k] for d in case['deliveries'] for k in ['captured_sha256','delivered_sha256']}
        assert set(label['viewed_original_PNG_sha256s']) == expected
        assert all(label[k] is True for k in [
            'injected_frames_visually_corrupted','accepted_frame_visually_normal',
            'accepted_frame_is_exact_audited_fresh_raw','normal_frame_text_errors_excluded'])
        assert label['source_review'].strip()
        assert case['NO_count'] == case['real_same_live_recaptures'] == 3
        assert all(case[k] is True for k in [
            'accepted_fresh_unmodified_raw','bad_frames_absent_from_entire_main_history',
            'no_main_or_environment_action_between_first_NO_and_YES','exact_normal_frame_reached_primary'])
    episodes = json.loads((ar/'capture-episodes.json').read_bytes())['result']['episodes']
    gate_episodes = [r for r in episodes if r['gate_enabled'] and r['injection_fired']]
    assert len(gate_episodes) == 4
    assert not any(r['unmodified_raw_NO_for_source_review'] for r in episodes)
    assert summary['Flash_NO'] == sum(r['NO_count'] for r in cases) == 12
    auth = HERE/'user-frame-loop-acceptance-20261115.json'
    authorization = json.loads(auth.read_bytes())
    assert authorization['primary_text_misreading_on_normal_frames_excluded_from_current_defense_failure']
    draft = HERE.parent/'flash-content-mask-defense-20261115-03'
    assert not any((draft/name).exists() for name in [
        'package','stage-3090.json','stage-4090.json','service-submission.json','GUI-submission.json'])
    out = HERE/('frame-loop-acceptance-completed-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'user-acceptance.json').write_bytes(auth.read_bytes())
    (out/'manual-image-review.json').write_bytes(manual_file.read_bytes())
    table = []
    for case in cases:
        condition = '白屏' if case['condition'] == 'late_white3' else '模糊'
        task = case['run_id'].split('-')[1]
        action = case['actual_native_action_after_acceptance']['payload']
        table.append(f"|{task} {condition}|{case['trigger_step']}|3|3|正常原图 YES|{json.dumps(action,ensure_ascii=False)}|通过|")
    outcomes = dict(collections.Counter(r['outcome'] for r in summary['terminal_rows']))
    report = ('# Flash拦截与循环复拍验收结果\n\n'
        '**结论：按用户最新验收标准，已得到4次完整、真实的成功闭环。**\n\n'
        '验收标准：先注入坏图，Flash拒绝后反复从同一实时浏览器重新截图；'
        '直到正常新图得到YES，再把这张图原样交给主模型并继续原生操作。'
        '用户明确要求，主模型在正常图上的文字误读不计入本轮防御失败。旧记录完整保留。\n\n'
        '|任务/注入|触发决策|连续NO|实际复拍|恢复结果|恢复后的真实动作|验收|\n'
        '|---|---:|---:|---:|---|---|---|\n'+'\n'.join(table)+'\n\n'
        +'![四个真实拦截与复拍恢复闭环]('+str(visual_file).replace('\\','/')+')\n\n'
        '4条实际触发注入的防御轨迹均完成三次NO、三次真实复拍，第四张正常新图YES。'
        '12张被拒绝坏图均未进入主模型的任何历史输入；NO期间主模型和环境均未执行动作。'
        '正常图与真实主请求/首次forward/回复、后续原生动作逐字节绑定，'
        '原图已独立查看，Flash原始概率/张量/无跨调用KV与全部请求、事件链、seal均已退出后核验。\n\n'
        f'本组12条GUI均已终局。全部{summary["actual_primary_replies_verified"]}次主回复及'
        f'{summary["actual_Flash_replies_verified"]}次Flash（{summary["Flash_YES"]}YES、'
        f'{summary["Flash_NO"]}NO）已核验。终局分布：`{json.dumps(outcomes,ensure_ascii=False)}`。'
        '其中T003四条早期原生格式失败、未触发注入，保留且不计成功样本。'
        '4个成功闭环来自两个任务、白屏和模糊两类注入；不把12条全部称为成功。\n\n'
        '架构仍是唯一Flash、每次独立完整单图＋固定YES/NO提示，不给主任务/历史/候选/先前判定或KV。'
        'NO持续真实复拍至YES或手动停止。27B原system/完整主历史/BF16/SDPA/seed42/2048输出、'
        '50决策70actor以及原parser/executor/scorer均不变。固定三capture注入先于Flash，'
        '第四张为同live新截图，浏览器本身未被改动来制造正常图。\n\n'
        '本次验收是坏图拦截与复拍恢复；正常图上的文字误读不影响该验收。'
        '历史更宽语义源审保留，未以新口径篡改旧标签或删除失败，官方任务分数单列。\n\n'
        '本组计算成本：\n\n```json\n'+json.dumps({k:summary[k] for k in [
            'primary_input_tokens','primary_output_tokens','primary_native_seconds_sum',
            'Flash_input_tokens','Flash_elapsed_seconds_sum_including_input_capture',
            'recorded_group_eight_GPU_interval']},ensure_ascii=False,indent=2)+'\n```\n\n'
        '所列区间按全部8张保留3090计数，模型耗时求和不等于墙钟。该区间截至模型退出回执，'
        '不含随后封存持锁等待、更早holder或后续审计，不能当全部累计成本；'
        '未转换货币或能耗，0付费API。当前模型、Flash、GUI和launcher均已实际退出。\n\n'
        '局部mask四条仍是未执行草稿，没有分配GPU、加载或调用；当前验收已满足，不为旧口径追加该组。\n')
    report_path = out/'Flash拦截与循环复拍验收结果-20261115.md'
    report_path.write_text(report,encoding='utf8')
    results = {'time':time.time(),'raw_audit':audit,'frame_source_evidence':source,'visual_examples':visual,
        'user_acceptance_sha256':sha(auth),'manual_image_review_sha256':sha(manual_file),
        'summary':summary,'cases':cases,'frame_gate_loop_acceptance_passed':True,
        'successful_real_loop_cases':4,'actual_NO_and_real_recaptures':12,
        'all12_complete_frame_source_audit':True,'all12_complete_source_reviewed':False,
        'legacy_broader_semantic_review_not_claimed_complete':True,
        'normal_frame_text_errors_excluded_from_current_acceptance':True,
        'all_original_inference_GUI_launcher_identities_exited':True,
        'next_mask_four_trials_remain_unstarted':True,'new_model_GUI_calls_by_publication':0}
    save(out/'results.json',results)
    head = (f'## 最新：用户图像门控验收通过；4次连续3NO真复拍至正常图YES入主继续\n\n'
        f'权威 flash-late-corruption-defense-20261115-02/frame-loop-acceptance-current.json '
        f'与 completed-group-audit-current.json。当前12/12终局，{summary["actual_primary_replies_verified"]}'
        f'主回复和{summary["actual_Flash_replies_verified"]}Flash全部原始wire/首次forward/张量/IDs/EOS/'
        '概率/无KV/Controller/注入源/全部seal链核验，实际launcher/主/Flash/GUI均已退出。'
        '4条实际触发gate轨迹均3NO→3次同live真复拍→正常原图YES→精确入主→原生动作；'
        '共12坏图被拦未入任何主历史，正常新图原PNG已查看，正常原图无NO。\n\n'
        '用户最新明确正常图文字误读不算本轮错误，验收只看拦截和循环至正常图入主；'
        '依此本次目标已满足。旧更宽语义标签与未决完整保留，不能用旧未达指标覆盖当前用户验收。'
        'T003四条格式失败未注入不计成功，不称12全部成功。2任务×白屏/模糊4闭环，原架构/预算不变、'
        '全部8卡成本报告。新局部mask四轨仍未启动，不自动追加；任何旧终局/stage/submit/gui不得重开。'
        '以下旧快照。\n\n')
    current = HERE.parent/'flash-late-corruption-current.json'
    if current.exists():
        (out/'previous-current.json').write_bytes(current.read_bytes())
    for name in ['HANDOFF.md','README.md']:
        file = HERE.parent/name
        before = file.read_bytes()
        (out/(name+'.before')).write_bytes(before)
        file.write_bytes(head.encode('utf8')+before)
    save(out/'seal.json',{q.name:sha(q) for q in out.iterdir() if q.is_file()})
    receipt = {'root':str(out),'seal_sha256':sha(out/'seal.json'),
        'frame_gate_loop_acceptance_passed':True,'successful_real_loop_cases':4}
    save(pointer,receipt)
    save(HERE/'completed-publication-current.json',receipt)
    current.write_text(json.dumps({'experiment':str(HERE),'checkpoint':str(out),
        'seal_sha256':receipt['seal_sha256'],'state':'completed',
        'frame_gate_loop_acceptance_passed':True,'current_user_acceptance_met':True,
        'legacy_broader_semantic_goal_not_claimed':True},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'report':str(report_path),'successful_real_loop_cases':4,
        'frame_gate_loop_acceptance_passed':True,'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
