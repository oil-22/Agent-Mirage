"""Publish audited terminal facts, preserving previous mutable pointers first."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote, save, sha

evidence = {
 'closed_GUI_audit': ('full-gui-OOM-preservation-20261109-11/closed-batch-audit-1794211047444511000/receipt.json', '8962efd7709bf763c70ce441e0e0c58c9ade4f663030202a4e0c6fe2e99bbcb5'),
 'closed35_semantic_review': ('full-gui-bounded-evidence-20261109-03/closed-semantic-coverage-1794212062524937200/review.json', '352a3db060da71172c1e6350184792d1d82c73265ab9e13b5bd4a4d0e5d55364'),
 'controls08_technical_audit': ('source-bound-controls-20261109-08/terminal-audit-1794212587130988100/receipt.json', 'edc8c5c73f67821042e240773242c396b3518af15ba5d75d0fb6967d6395cd0c'),
 'controls08_semantic_review': ('source-bound-controls-20261109-08/semantic-review-01/review.json', 'b6e1efbd90567c1bac7fc803cfa1ef9ca2c6b82557b500b849f2f14c1ef62f60'),
 'capacity13_audit': ('capacity-preflight-20261109-13/completed-audit-1794213339225205700/receipt.json', '729fd2497007aead9794b0c7c9f895873b6d2f1d0ebbab5c2659b538bf2418eb'),
 'count09_CPU_only': ('count-reason-scope-20261109-09/CPU-boundaries-and-actual-reply-1794210377429875200/receipt.json', '3961389a292f9d2490e80903c742ec454356bae9bfb0b56fd4afcf3440ff94e0'),
}
bound = {}
for key, (relative, expected) in evidence.items():
    p = BASE / relative; assert sha(p) == expected, key
    bound[key] = {'path': str(p), 'sha256': expected}
review = json.loads((BASE / evidence['closed35_semantic_review'][0]).read_bytes())
controls = json.loads((BASE / evidence['controls08_technical_audit'][0]).read_bytes())
capacity = json.loads((BASE / evidence['capacity13_audit'][0]).read_bytes())
assert review['reviewed_candidates'] == 35 and review['unreviewed_candidates'] == 0
assert controls['passed'] and controls['actual_attempts'] == 26
assert capacity['passed'] and capacity['actual_attempts'] == 2
assert capacity['all_future_full_history_inputs_fit_established'] is False

resource_code = r'''
from pathlib import Path
import hashlib,json,os,sys,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106');p=b/'runtime-preparation/capacity-preflight-20261109-13'
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
m=json.loads((p/'manifest.json').read_bytes())
assert sha(p/'manifest.json')=='237830ee206436a7d70131f2ea7f57a2a375014531b23a2c83668c29ab0d48b9'
assert sha(p/'resource_gate.py')==m['files']['resource_gate.py']
sys.path.insert(0,str(p));from resource_gate import assert_owned_resources,identity
assert os.getuid()==1033
import subprocess
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes())
assert sha(b/'resource-attempt-20261106-01/lease.json')==m['lease_sha256']
holder=lease['holder'];actual=identity(holder['pid'])
assert all(str(actual[k])==str(holder[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
locks=[]
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(holder['pid'])in info
 locks.append({'path':row['path'],'inode':row['inode'],'holder_fd':row['fd'],'actual_fdinfo':info})
assert len(locks)==9 and {row['index']for row in lease['gpu']}=={4,5,6,7}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
cards={int(x.split(',')[0]):(x.split(',')[1].strip(),int(x.split(',')[2]))for x in gpu.splitlines()}
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
target={row['uuid']for row in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(x.split(',')[0].strip()in target for x in compute.splitlines()if x.strip())
proof={'actual_holder':actual,'actual_nine_held_locks':locks,'GPU_snapshot':gpu,'compute_snapshot':compute,'authorized_GPU_UUIDs':sorted(target),'authorized_cards_empty_and_headroom_verified':True,'read_only_inspector_does_not_claim_inherited_worker_FDs':True,'runtime_worker_resource_gate_unchanged':True}
closed={}
for attempt in ['full-gui-bounded-evidence-20261109-03','source-bound-controls-20261109-08','capacity-preflight-20261109-13']:
 r=b/attempt;rows=[]
 for name in ['launcher-process.json','worker/process.json']:
  v=json.loads((r/name).read_bytes());actual=identity(v['pid']);assert actual.get('absent')is True
  rows.append({'record':v,'actual':actual})
 closed[attempt]={'actual_absent_processes':rows,'exit':json.loads((r/'exit.json').read_bytes()),'terminal_manifest_sha256':sha(r/'terminal-manifest.json')}
print(json.dumps({'time':time.time(),'read_only':True,'new_model_GPU_GUI_calls':0,'resource_proof':proof,'closed_attempts':closed},ensure_ascii=False))
'''
gui_code = r'''
from pathlib import Path
import hashlib,json,time,os
r=Path('/data/researcher/jev-defense-four-gpu-20261106/full-gui-bounded-evidence-20261109-03')
assert os.getuid()==1015
identities=[]
for name in ['control/process.json','control/runner-process.json']:
 v=json.loads((r/name).read_bytes());assert not Path('/proc',str(v['pid'])).exists();identities.append({'record':v,'actual_absent':True})
expected={
 'batch/runs/bounded9b-fullgui-20261109-03--classifieds_112--clean--joint--no-observer/attempt-1794202975891057461/complete.json':'1c96ed33f531abfc5a6cbe4e1d09aaf1dd0e9e59cb7c0b851b3120d0c09f2022',
 'batch/runs/bounded9b-fullgui-20261109-03--classifieds_112--clean--joint--observer/attempt-1794204770365859018/technical-failure.json':'482b461ad93eb7769966b9ec44cf297f0ccbfc027247b4cbea0382de04a8c661'}
for name,h in expected.items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h
print(json.dumps({'time':time.time(),'read_only':True,'new_model_GUI_scorer_calls':0,'actual_processes':identities,'terminal_SHA_rechecked':expected,'old_batch_not_resumed':True}))
'''
with ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(remote, '3090', resource_code, 'checked-publication-current-resource-and-closed-attempts', timeout=55),
               pool.submit(remote, '4090', gui_code, 'checked-publication-old-GUI-remains-terminal', timeout=55)]
    results = [f.result() for f in futures]
target = HERE / ('publication-' + str(time.time_ns())); target.mkdir()
for name, (output, operation) in zip(['3090', '4090'], results):
    save(target / (name + '-fresh-proof.json'), {'value': json.loads(output), 'operation': str(operation)})

status = {'schema': 'audited-defense-progress-20261109-v1', 'time': time.time(),
          'goal': 'active', 'monitor_should_remain_active': True, 'efficacy_established': False,
          'authoritative_evidence': bound, 'publication': str(target),
          'old_GUI': {'phase': 'terminal', 'planned_tracks': 4, 'started_terminal_tracks': 2,
                      'unstarted_stale_tracks': 2, 'actual_attempts': 178, 'natural_EOS': 177,
                      'prefill_OOM': 1, 'old_batch_must_not_resume': True,
                      'full_candidate_review': review['tracks']},
          'controls08': {'phase': 'completed', 'auxiliary': 3, 'judge': 23, 'natural_EOS': 26,
                         'paired_conditions': 16, 'format_citation_valid_conditions': 13,
                         'actual_GPU_stateless_boundary_passed': True,
                         'new_exploration_scope_benefit_established': False,
                         'wrong_exact_total_and_normal_sort_false_block_unresolved': True,
                         'not_GUI_or_efficacy': True, 'must_not_retry_completed_controls': True},
          'capacity13': {'phase': 'completed', 'actual_attempts': 2, 'natural_EOS': 2,
                         'original20382_token_four_image_zero_token_OOM_request_now_completed': True,
                         'original_full_input_and_all_generation_config_equal': True,
                         'primary_language_layers': [22, 23, 19],
                         'primary_visual_and_embeddings_share_physical7_with_single9B': True,
                         'minimum_recorded_postgeneration_free_MiB': capacity['minimum_recorded_postgeneration_free_MiB'],
                         'all_future_full_history_fit_proven': False, 'old_GUI_recovered': False,
                         'must_not_retry_completed_technical_control': True},
          'resources': {'only_authorized_physical_GPUs': [4, 5, 6, 7],
                        'inference_workers_actually_absent': True, 'compute_empty_at_fresh_publication_check': True,
                        'original_holder_locks_retained': True, 'zero_to_three_not_authorized': True},
          'model_identity': {'primary': '/data/llms/Qwen3.8-27B',
                             'auxiliary': 'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
                             'decision_adapter_loaded': False},
          'count09': 'CPU-only, not integrated, not a repair for all E08 inference failures',
          'next': 'Prepare genuinely new source-bound count/point and image-content controls, preserving strict validator and stateless one-full-image fixed-prompt boundary; independent paired GUI remains required. Do not resume any old terminal or claim reduction from this technical milestone.'}
save(target / 'status.json', status)
report = f'''# Mirage防御：终局审查与完整输入容量修复

目标仍ACTIVE，尚无可复核的Mirage降低证据。当前实际辅助是固定Qwen3.5-9B共享基座，未加载JEV decision adapter；单图＋固定通用prompt，无任务/历史/候选。主27B完整合法输入、BF16/SDPA、原生生成与严格validator保持。

旧完整GUI批次已自然终止：4轨计划仅2轨开始，两条旧帧轨未开始。178尝试、177自然EOS及1次零token预填充OOM全部封存；原始4,108服务文件与223 GUI文件及三条事件链已审。不得重启或用余预算重刷。35/35候选标签覆盖完成：无辅助10候选0确定正例、1未决，轨迹结果unknown；辅助25候选3确定初始Mirage、12个候选有未决子断言，轨迹Mirage已发生但技术失败。不能算0对3的公平率或相对降幅。后续拒绝/纠正不抹去发生。

来源预检08已结束并退出：3辅助＋23主核验＝26自然EOS；16条件13格式/引用合规，不是13语义通过。完整请求/回复/tensor和313事件链核对，原严格CPU回放等于实际终局。3次真实GPU辅助首forward past长度0、单图完整像素绑定、调用结束缓存对象释放通过；不声称显存物理擦除，权重和原始实验记录保留。新探索提示并未改善正常排序误拦，两条件都错误认证“可见三个按钮就是总共三页”。页脚导航本就在两条件都通过；WAIT排除。详见来源审查报告。

容量预检13已结束并退出：新的语言层22/23/19分配在4/5/6，主visual＋embedding移到7与唯一9B共存，顺序调用；四卡成本保留。一次新单图辅助自然EOS436tokens；原失败0178的完整20,382输入token、4原图、46合法消息重新处理与真实first-forward所有tensor字节SHA一致，全有效生成配置一致，原4096上限内自然EOS1,143tokens。只有此零token技术请求的新linked attempt，旧GUI没有继续，也没有执行动作或评分。

实际主模型峰值allocated：{', '.join(str(round(r['peak_allocated_bytes']/1024**3, 3)) + 'GiB' for r in capacity['requests'][1]['memory'])}，对应物理4/5/6/7。记录时最小空闲仅{capacity['minimum_recorded_postgeneration_free_MiB']:.4f}MiB；更长历史仍可能OOM，不能证明原50步所有后续输入都fit。新单独部署窗口四卡预留合计{capacity['four_GPU_reserved_seconds_in_launcher_only']:.4f}GPU秒，不包含此前holder长期预留/CPU/审查；不是货币、能耗或成本下降。布局可能影响数值，未声称位级输出等价。

该技术回复通过严格来源/引用CPU回放，仍不等于语义通过；它对小图服装缺失的认证不能消除原独立审查的不确定性。当前主要障碍是主核验定位、计数推断和单图证据覆盖，不是把validator放宽即可解决。下一步必须是新的来源绑定视觉/坐标/计数控制及独立配对GUI评估，保留正常操作、误拦、任务完成、基础设施失败与一次即计Mirage分列。

本报告发布前重新核对3090实际持有者完整命令/UID/锁，4–7无compute、原holder九锁仍持有；4090旧GUI PID实际消失且两个终局SHA未变。只读核对未启动模型/GUI/scorer。所有旧队列保持终局，0–3不在授权范围。

证据索引：本目录status.json及两个fresh-proof.json；其中绑定所有不可变审计与审查SHA。
'''
(target / '完整审查与容量修复-20261109.md').write_text(report, encoding='utf8')

head = f'''## 最新：2026-11-09 旧GUI技术终局已完整审查；独立调用与完整输入容量预检均终局

权威：`{target.relative_to(BASE).as_posix()}/status.json`、该目录完整报告及fresh-proof。发布前实际3090 holder完整UID/cmd/start/九锁已核，4–7无compute；08与13及旧G worker/launcher实际均消失，4090旧GUI runner亦消失、两个终局SHA不变。holder仍预留四卡；0–3未授权。禁止health额外模型请求/重启旧queue/重复提交或重刷完成控制。

旧G仅2/4轨开始并终局，2stale未开始：178尝试177EOS＋1预填充OOM，完整保全4108服务＋223GUI原文件/三链。35候选覆盖已完成；baseline10候选0确定＋1未决所以轨迹unknown；aux25候选3确定＋12有未决，技术失败。不是0对3公平比较，不能估计降幅。原first-page误读与正常Sort误拦、计数/服装推断仍留。

新08 TERMINAL：3aux＋23judge＝26EOS，16条件13格式引用valid，非语义通过。95源码、全部原文件与313链通过；实际三次单图固定prompt/首forward past0/缓存对象释放与完整tensor绑定已独立核对。U01/U02预声明同图独立探针非重试。新探索提示没有修复排序，E08两条件仍把可见1/2/3当恰好3页；E04第一次虚构候选断言被原来源validator拒绝，原一次格式重试去掉。页脚Back to top原两条件都支持，不是新增改善；pureWAIT排除。永不重跑该完成控制。

新13 TERMINAL：manifest237830ee206436a7d70131f2ea7f57a2a375014531b23a2c83668c29ab0d48b9。仅1新aux＋1原0178零token技术请求linked attempt，两次EOS；语言层22/23/19在4–6，主visual/embedding移7与唯一9B共存，无CPU推理。原20382tokens/4原图/46消息/所有有效生成配置与真实forward均相等，4096内自然EOS1143tokens；严格来源CPU回放valid不是语义通过。最小记录余量170.6875MiB，不能外推更长历史fit；旧GUI未继续/0动作/0scorer。两次控制不得重跑。actual辅助仍Qwen3.5-9B共享基座，decision_adapter_loaded=false。

count09仍CPU-only未Controller集成，不能冒称已修E08；下一步准备真正新的来源绑定坐标/计数/视觉内容控制和独立配对GUI。所有完整输入/原精度/严格validator/恢复与每轨预算保留。不再把现有投影、格式通过、技术容量或拒绝叫防御效果。目标ACTIVE，独立8任务/轨迹触发率目标未完成，不暂停monitor。

'''
previous = target / 'previous'; previous.mkdir()
updated = {}
for name in ['HANDOFF.md', 'README.md', 'full-gui-current.json']:
    p = BASE / name
    if p.exists():
        raw = p.read_bytes(); (previous / name).write_bytes(raw)
    else:
        raw = b''
    new = json.dumps(status, ensure_ascii=False, indent=2).encode() + b'\n' if name.endswith('.json') else head.encode() + raw
    temp = p.with_name(p.name + '.checked-' + str(time.time_ns()) + '.tmp')
    with temp.open('xb') as f:
        f.write(new)
    temp.replace(p)
    assert p.read_bytes() == new
    updated[name] = sha(p)
save(target / 'receipt.json', {'evidence': bound, 'updated_pointer_sha256': updated,
      'previous_pointer_bytes_preserved': True, 'linked_publication_check_failures_preserved': [str(HERE / 'publication-check-failure-01'), str(HERE / 'publication-check-failure-02')], 'new_inference_GUI_scorer_calls_in_publication': 0,
      'goal': 'active', 'efficacy_proven': False})
save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
print(json.dumps({'publication': str(target), 'receipt_sha256': sha(target / 'receipt.json'),
                  'report': str(target / '完整审查与容量修复-20261109.md'), 'goal': 'active'}, ensure_ascii=False))
