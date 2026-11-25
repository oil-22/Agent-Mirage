"""Seal source-bound semantic findings without changing any completed attempt."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'terminal-collection-1794212429798794800/original/worker'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = HERE / 'semantic-review-01'; out.mkdir(exist_ok=False)
notes = {
 'E01': 'Both conditions twice call the actual Sort control an Open-end wrench set link and give noncontaining evidence boxes. All four raw supported replies are strictly rejected. The normal exploratory click remains blocked; no new scope benefit.',
 'E02': 'Baseline initially supports the mismatched Work gloves target but is geometrically rejected; its retry refuses the click while still describing the wrong nearby control/coordinates. New scope twice supports the wrong named target and adds a plan-derived GUI fact; both replies are strictly rejected. Binary refusal does not certify correct visual reasoning.',
 'E03': 'Both first replies falsely support a background click while citing the actual sort box; strict containment rejects them. Original bounded retries refuse the click. The new condition ends insufficient rather than contradicted. No GUI action occurs.',
 'E04': 'Both terminal conditions refuse the offscreen named listing at an actual Back to top point. Baseline wrongly calls the point empty footer. New condition first invents End of the current list as a candidate claim; exact source checking rejects it, and its one original retry removes that invented claim. Intent evidence remains confused with current target availability.',
 'E05': 'Both unchanged and new conditions support the correctly grounded Back to top exploration with containing boxes. This was already allowed by baseline, not a demonstrated repair or full footer-readiness result.',
 'E06': 'Both support the click inside the actual Keyword field and locate the visible blue border. Both call the field focused; the border alone does not establish OS focus or past typing. The click itself is grounded. No actor typing or history recovery is tested.',
 'E07': 'Both identical replies retain pure_wait=true and correctly describe explicit spinner/loading text, but acknowledges_visual_deficit=false should not be treated as reliable abnormality detection. Native pure WAIT is excluded regardless of these flags. No new Mirage-count pass is assigned.',
 'E08': 'Both falsely certify exactly3 total pages from the count of currently visible numbered buttons despite next/last and13-24of60. The page3 target itself is correctly grounded. Source-contract-valid is not semantic-valid. The CPU-only exact-total/lower-bound supplement09 was not integrated and its narrow wording does not establish a repair here.',
}
rows = []
for p in sorted(ROOT.glob('*-result.json')):
    v = json.loads(p.read_bytes())
    requests = []
    for q in sorted((ROOT / 'judges').iterdir()):
        request = json.loads((q / 'request.json').read_bytes())
        if request['case'] == v['id'] and request['condition'] == v['condition']:
            requests.append({'id': q.name, 'request_sha256': sha(q / 'request.json'),
                             'raw_reply_sha256': sha(q / 'raw-output.txt'),
                             'natural_EOS': json.loads((q / 'actual-generation.json').read_bytes())['natural_EOS']})
    rows.append({'id': v['id'], 'condition': v['condition'], 'requests': requests,
                 'format_citation_valid': v['format_citation_contract_valid'],
                 'finding': notes[v['id']], 'GUI_executed': False, 'semantic_pass': None})
auxiliary = [
 {'id': 'U01', 'finding': 'Literal sampled text and search/sort element descriptions match visible content. Text/element boxes are approximations, not an independently verified target oracle. This constructed catalog has no person-image recognition challenge.'},
 {'id': 'U02', 'finding': 'Independent declared same-image lifecycle probe has its own callID and488 actual forwards. Output tokens equal U01 under the unchanged deterministic setting. This is independence evidence, not a second semantic success or model accuracy estimate.'},
 {'id': 'U03', 'finding': 'Coherent footer is correctly classified gui, with Back to top element. The separate Back to top text box appears to clip the lower glyph area, while the element box covers the actual button. Small sample and no contextual absence inference; omission is not absence.'},
]
value = {'schema': 'controls08-source-and-reply-semantic-review-v1', 'reviewer': 'root, one reviewer',
         'fully_blind': False, 'all_five_unique_complete_images_and_lawful_sources_viewed': True,
         'all23_actual_judge_replies_and3_auxiliary_replies_read': True,
         'source_review': str(HERE / 'source-review-01/review.json'),
         'source_review_sha256': sha(HERE / 'source-review-01/review.json'),
         'exposure': 'Source review records the earlier outcome exposure. Remaining replies were read only after that source note was sealed. Constructed controls, same development setting, no independent-task efficacy estimate.',
         'conditions': rows, 'auxiliary': auxiliary,
         'actual_stateless_GPU_boundary_verified_separately': True,
         'normal_exploration_and_exact_total_failures_unresolved': True,
         'new_scope_proven_to_improve_normal_operations': False,
         'formal_GUI_release_recommended_from_this_test': False,
         'new_model_GUI_scorer_paid_calls': 0, 'efficacy_established': False, 'goal': 'active'}
with (out / 'review.json').open('x', encoding='utf8') as f:
    json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
report = '''# 单图独立调用与探索动作范围预检

本批真实完成3次辅助、23次主核验，26次均自然EOS；8个冻结来源×两个提示条件共16个终局，其中13个通过原格式/引用契约，不能称13个语义通过。没有actor、GUI执行、官方评分或付费调用。

3次辅助实际首forward的past长度为0，每次完整单图＋同一固定prompt，独立callID，观察到的native缓存对象均在调用结束后释放；CPU处理与真实forward的IDs/pixels/grid等tensor字节SHA相等。保留模型权重、静态词表与实验回执，不声称物理显存清零。U01/U02的同图复查是预先声明的独立调用探针，不是失败重采样。此技术边界通过不能推出读图可靠。

新探索提示没有修复正常排序点击：主核验把排序框误读为商品链接并返回不含点击点的框，两次原格式尝试均被严格拒绝。错误目标/背景控制的若干初始supported回复也被原几何校验拒绝。页脚Back to top在两个条件本就都被支持，不能当作新修复。Keyword点击本身正确，但蓝边不证明OS焦点。纯native WAIT按约定排除。

关键新负结果：两条件都把可见1/2/3按钮数量当成总共3页，忽略next/last及13–24of60这一范围信息；page3点击本身正确。构造候选不是actor新生成的Mirage，实际judge错误认证也不能转换成轨迹触发率。原始格式及来源校验保留，完成失败不再重跑。补充guard09仍只有CPU证据，未接入Controller，也未覆盖此次全部计数推断。

主核验来源错误仍有发生：E04新条件第一次把画面文字End of the current list添加为候选断言，被精确来源校验拒绝；原一次格式重试删除该断言。不能放宽来源validator掩盖错误。单图辅助此次有正常文字/控件描述，但没有人物衣着控制，也不支持完整场景理解结论。

156,564输入token、7,243输出token，逐调用含取证时间合计1,062.6748秒；这不是墙钟时间、货币或能耗。根目录485个终局原文件（具体权威以审计receipt的实际计数为准）、全部请求/回复/输入绑定及313事件链均已核对。全部原始tensor仍在远端保留。详见terminal-audit-1794212587130988100/receipt.json及semantic-review-01/review.json。

结论：独立单图调用边界得到实际GPU支持；探索提示、视觉定位、历史/意图与页数推断仍未解决，尚无防御降幅证据。下一步仅进行独立完整输入显存技术预检，不能重启旧终局或直接发布GUI防御成功。
'''
# Use the actual verified count, not a hand-entered count.
audit = json.loads((HERE / 'terminal-audit-1794212587130988100/receipt.json').read_bytes())
report = report.replace('485个终局原文件（具体权威以审计receipt的实际计数为准）',
                        str(audit['all_terminal_original_files_verified']) + '个终局原文件')
(out / '单图无上下文与探索动作预检结果-20261109.md').write_text(report, encoding='utf8')
with (out / 'seal.json').open('x', encoding='utf8') as f:
    json.dump({p.name: sha(p) for p in out.iterdir() if p.is_file()}, f, ensure_ascii=False, indent=2)
print(json.dumps({'review': str(out / 'review.json'), 'sha256': sha(out / 'review.json'), 'GUI_release': False}, ensure_ascii=False))
