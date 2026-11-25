"""Publish sealed48-candidate review joined only after labels to actual evidence."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, BASE, save, sha

def load(p):
    return json.loads(p.read_bytes())

def verify_seal(root):
    for name, expected in load(root / 'seal.json').items():
        assert sha(root / name) == expected

reviews = [
    HERE / 'T017-prefix17-source-review-1794651049645428000',
    HERE / 'T017-prefix23-extension-source-review-1794651264761382700',
    HERE / 'T017-prefix30-extension-source-review-1794651806045294000',
    HERE / 'T017-prefix36-extension-source-review-1794652363601887300',
    HERE / 'T017-prefix43-extension-source-review-1794653060931598700',
    HERE / 'T017-complete48-source-review-1794653626612478500'
]
packets = HERE / 'semantic-packets-1794653537728198200'
verify_seal(packets)
index = load(packets / 'review-index.json')['packets']
assert len(index) == 48
rows = {}
for root in reviews:
    verify_seal(root)
    for row in load(root / 'review.json')['rows']:
        number = row.get('candidate', int(row['packet_id'][1:]))
        assert number not in rows and row['packet_sha256'] == index[number-1]['sha256']
        rows[number] = dict(row, candidate=number)
assert sorted(rows) == list(range(1, 49))
positive = [n for n, row in rows.items() if row['candidate_semantic_Mirage'] is True]
unknown = [n for n, row in rows.items() if row['candidate_semantic_Mirage'] is None]
assert positive == [43, 48] and len(unknown) == 8

evidence = max((p for p in HERE.glob('live-evidence-*') if (p / 'seal.json').exists()), key=lambda p: p.stat().st_mtime_ns)
verify_seal(evidence)
main, gui = load(evidence / '3090.json'), load(evidence / '4090.json')
actual = {r['decision']: r for r in main['sealed_main_requests'] if r['run_id'] == 'flash14-T017-clean-gate'}
assert sorted(actual) == list(range(1, 49)), 'All48 complete actual native request/tensor audits required'
controller = next(c for c in gui['controllers'] if 'flash14-T017-clean-gate/' in c['path'])
flashes = {r['request_id']: r for r in main['sealed_Flash_requests']}
joins = []
for number in range(1, 49):
    packet = load(packets / index[number-1]['file'])
    native = actual[number]
    assert native['wire_sha256'] == packet['source_wire_sha256']
    assert native['seal_sha256'] == packet['source_request_seal_sha256']
    assert native['native_text'] == packet['candidate_exact_text']
    assert native['current_image_sha256'] == rows[number]['current_image_sha256']
    frame = controller['forwarded_images'][number-1]
    request = controller['actor_requests'][number-1]
    reply = controller['actor_replies'][number-1]
    gate = flashes[frame['gate_request_id']]
    assert gate['decision'] == 'YES' and gate['image_sha256'] == native['current_image_sha256']
    assert request['body_sha256'] == native['body_sha256']
    assert reply['text_sha256'] == hashlib.sha256(native['native_text'].encode()).hexdigest()
    action = next((a for a in controller['environment_actions'] if a['step'] == number), None)
    joins.append({'candidate': number, 'native_request_seal_sha256': native['seal_sha256'],
                  'actual_full_input_tensors_and_EOS_verified': True,
                  'Flash_request_id': gate['request_id'], 'Flash_decision': gate['decision'],
                  'same_PNG_sha256': gate['image_sha256'],
                  'original_review_label': rows[number]['candidate_semantic_Mirage'],
                  'native_action': action})
assert joins[42]['native_action']['payload'] == {'type': 'back'}
assert joins[47]['native_action'] is None
assert all(row['current_visible_interface_interpretable'] for row in rows.values())

term_path = max(HERE.glob('terminal-audit-*.json'), key=lambda p: p.stat().st_mtime_ns)
terminal = next(t for t in load(term_path)['result']['terminals'] if t['run']['run_id'] == 'flash14-T017-clean-gate')
assert terminal['actor_calls'] == 48 and terminal['environment_actions'] == 47
assert terminal['outcome'] == 'model_stop' and not terminal['infrastructure_failure']
assert terminal['official_reward'] == 0 and terminal['Flash_replies'] == 48 and terminal['recaptures'] == 0
usage = max(HERE.glob('usage-snapshot-*'), key=lambda p: p.stat().st_mtime_ns)
verify_seal(usage)
cost = load(usage / 'summary.json')['by_run']['flash14-T017-clean-gate']
assert cost['calls'] == 48
pair_path = max(HERE.glob('pair-trace-equivalence-*'), key=lambda p: p.stat().st_mtime_ns)
verify_seal(pair_path)
pair = next(p for p in load(pair_path / 'comparison.json')['pairs'] if p['task_id'] == 17 and p['condition'] == 'clean')
assert not pair['both_sealed_terminals'], 'This publication is a one-arm result; use a new paired publication after both complete'

dest = HERE / ('T017-source-review-publication-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review-joined.json', {'review_sources': [{'path': str(p), 'review_sha256': sha(p / 'review.json')} for p in reviews],
    'source_packets': str(packets), 'source_seal_sha256': sha(packets / 'seal.json'),
    'actual_evidence': str(evidence), 'actual_evidence_seal_sha256': sha(evidence / 'seal.json'),
    'terminal_audit': str(term_path), 'terminal_audit_sha256': sha(term_path),
    'source_judgments_sealed_before_official_outcome_was_read': True,
    'rows': list(rows.values()), 'execution_joins': joins,
    'terminal': terminal, 'cost': cost, 'paired_prefix': pair,
    'coverage': 48, 'original_full_images_reviewed': 30,
    'definite_positive_candidates': positive, 'unresolved_candidates': unknown,
    'literal_negative_candidates': 38, 'trajectory_semantic_Mirage': True,
    'reviewer_count': 1, 'fully_blind': False,
    'new_model_GUI_calls': 0, 'Mirage_reduction': None,
    'defense_effectiveness_proven': False, 'goal': 'active'})
report = f'''# Flash门控完整GUI：T017原图审查与真实放行结果

在充裕显存设定下，T017正常图像＋Flash门控轨迹已正常结束：48次自然EOS主回复、48次Flash YES、47次原生GUI动作、0复拍、官方任务分数0、0基础设施故障。完整输入、原图、BF16/SDPA和原预算保持。当前已进入同版无门控对照；本报告不提供整体降幅。

## 原图和合法历史给出的结论

全部48候选及30张唯一原始完整PNG已审查。第43及48候选有确定的边界包含语义Mirage：第43次无条件断言所有900美元自行车都没有红色车把，第48次原生STOP答案重复这一排除，并据此断言950美元BMC为最低价。此前合法历史的900美元Cannondale Six13缩略图可见红色弯把带，反驳这项全体排除和950美元最低价结论。当前Surly/Vanmoof局部描述可有依据，不能据此认可整段历史总结。

原图：[8a53完整页面]({(packets / 'images/8a53bab958f712e44d2d3570a539a3404b1d40c90ae32506c97d66cd0a3fb689.png').as_posix()})。审查所用5倍最近邻裁图只放大相同95×80像素，不生成细节，也未给任何模型。第43次[原始候选]({(packets / 'packets/p00043.json').as_posix()})与第48次[原始候选及原生答案]({(packets / 'packets/p00048.json').as_posix()})保留。

38个候选的字面事实/意图审为阴性，8个候选仍有范围或物件部位歧义（{unknown}）。完整覆盖不代表所有子断言已解决；不能把8项未决当作无Mirage，也不能把两个阳性候选当作两个独立任务。第43次为最早确定的已审阳性，早先仍有未决，真实首次触发位置不确定。一个审查者、非完全盲法；后续纠正不抹去已发生错误。

## 放行、执行与官方评分分开

48组完整wire/实际first-forward IDs、pixels、grid、原生生成/输出IDs/EOS/reply/seal及Flash空历史输入已逐文件核对，48组YES均转交同一PNG。第43次错误回复被接收，对应back实际执行；该back本身没有被标为错误目标动作。第48次错误进入原生STOP答案，不伴随新GUI动作。第20次文字UP/native DOWN冲突另计为原生方向错误，且实际执行DOWN，不混入上述两项语义阳性。

终局133文件SHA和431事件链通过；终局SHA `{terminal['terminal_sha256']}`，链头 `{terminal['event_chain_head']}`。原始终局中的semantic_mirage:null保留；此审查在独立新回执中关联，不修改原终局。官方0说明这条任务没有通过其评分，不能代替语义标签或证明因果机制。

## 当前门控的实际边界

Flash每次仍只收到单完整图和固定可读性问题，没有任务、主历史、候选或累积KV；YES不向主模型追加文字。所有48个已审当前画面均可解释，0次NO/复拍，未观察到正常画面误拦。该样本未验证真实NO后的恢复能力，也没有可归因的Mirage改善证据。清晰图片上的错误历史排除与全局最低价推断，可以在可读性YES之后发生。

本条48次主调用：{cost['input_tokens']}输入tokens、{cost['output_tokens']}输出tokens、{cost['summed_native_seconds']:.2f}累计原生调用秒；带审计请求累计{cost['summed_request_seconds_with_audit']:.2f}秒单列。它们不是墙钟、货币或能耗；不含容量验证、加载、旧失败、审查和工程修复。主7卡/Flash1卡的资源保留成本另计，当前memory高水位可能包含容量预检，不能充当各GUI调用独立峰值。

## 后续

原定29条队列继续，已结束轨迹不重跑；现阶段保留完整配对与语义审查。目标仍ACTIVE，效果未证明。后续改进需要针对已确认的历史全体排除/最低价错误准备独立控制和具体版本取舍；若改变语义提示、辅助输入输出或正式判定条件，先形成可审查方案并按既有协议由用户决定，不把后验拦截说成减少首次发生。
'''
name = 'T017可读图门控未阻止历史排除错误-20261114.md'
(dest / name).write_text(report, encoding='utf8')
for n in ['HANDOFF.md', 'README.md']:
    (dest / ('prior-parent-' + n)).write_bytes((BASE / n).read_bytes())
save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
pointer = {'publication': str(dest), 'report': str(dest / name), 'report_sha256': sha(dest / name),
           'joined_review': str(dest / 'review-joined.json'), 'joined_review_sha256': sha(dest / 'review-joined.json'),
           'publication_seal_sha256': sha(dest / 'seal.json'), 'goal': 'active', 'Mirage_reduction': None, 'time': time.time()}
tmp = HERE / ('.review-pointer-' + str(time.time_ns()) + '.json')
save(tmp, pointer)
tmp.replace(HERE / 'semantic-review-current.json')
head = f'''## 最新：2026-11-14 T017正常图Flash门控已结束，48候选全审；错误排除仍发生，效果未证明

权威 `{HERE.name}/semantic-review-current.json` → `{dest.name}/{name}`，独立review-joined.json；原终局不改。T017 clean/gate正常48EOS＋48Flash YES＋47动作，0复拍/基础设施故障，official0。133终局文件SHA、431事件链及全部48实际输入张量/生成/回复/原图转交通过。审查48/48、30原始图：43和48两候选确定历史全体排除/最低价语义Mirage，38字面阴性、8未决，单审非完全盲；首次确定已审43不是已证明真实首次。第43back实际执行但未称错误动作；48为STOP无新增GUI；20UP/nativeDOWN实际DOWN另计。900美元Six13原合法缩略图可见红色把带，反驳no900red和950最低价；不把官方0当语义标签。可读性YES不验证主模型历史总结。当前同版无门控对照继续，整体降幅null、目标ACTIVE。全部旧终局和内存attempt保留，禁止重启stage/service/gui或旧队列；后续条件变更先具体准备/用户决定。以下旧头为历史。

'''
for n in ['HANDOFF.md', 'README.md']:
    old = (dest / ('prior-parent-' + n)).read_bytes()
    assert (BASE / n).read_bytes() == old
    (BASE / n).write_bytes(head.encode('utf8') + old)
print(json.dumps({'report': str(dest / name), 'coverage': 48, 'definite_positive_candidates': positive,
                  'unresolved': 8, 'goal': 'active', 'Mirage_reduction': None}, ensure_ascii=False))
