"""Publish a new immutable checked snapshot; preserve every prior handoff head."""
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
GUI=BASE/'full-gui-bounded-evidence-20261109-03'
out=GUI/('publication-checked-'+str(time.time_ns()));out.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
service=GUI/'operations/1794206746882254600-inspect-service/stdout.txt'
gui=GUI/'operations/1794206746882752300-inspect-full-GUI/stdout.txt'
s=json.loads(service.read_bytes());g=json.loads(gui.read_bytes())
actual=s['worker/process.json']['value']['actual'];assert actual['uid']==1033 and actual['pid']==3959659
assert len(s['held_locks'])==9 and g['control/runner-process.json']['value']['actual']['uid']==1015
diag=BASE/'auxiliary-grammar-isolation-20261109-06/diagnostic-collection/1794205640887040400/original/receipt.json'
admit=BASE/'auxiliary-grammar-isolation-20261109-06/integration-linked02-admission-1794206276027804700/receipt.json'
actual_input=HERE/'actual-input-audit-1794206718865243900/receipt.json'
labels=GUI/'semantic-review-candidates-eighteen-twenty-01/labels.json'
value={'time':time.time(),'stage':'live_GUI_plus_source_bound_repairs_and_user_stateless_boundary',
 'root':str(GUI),'service_snapshot':str(service),'service_snapshot_sha256':sha(service),
 'GUI_snapshot':str(gui),'GUI_snapshot_sha256':sha(gui),
 'snapshot_time_unix':s['time'],'actual_model_attempts_at_snapshot':105,
 'completed_tracks_at_snapshot':1,'expected_tracks':4,
 'first_track':{'condition':'clean/noaux','actor':10,'judge':39,'EOS':49,'actions':6,
  'official_reward':0,'terminal':'blocked/regeneration_cap','technical_failure_reported':False,
  'terminal_sha256':'1c96ed33f531abfc5a6cbe4e1d09aaf1dd0e9e59cb7c0b851b3120d0c09f2022',
  'full_closed_track_audit':str(GUI/'closed-first-track-audit/1794205070152982200/receipt.json'),
  'candidate_labels_reviewed':10,'definite_Mirage_observed':0,'unresolved_uniqueness_candidates':1,'trajectory_Mirage_endpoint':'unknown'},
 'second_track_at_snapshot':{'condition':'clean/one_aux','actor':11,'judge_attempts':36,'auxiliary':9,
  'actual_actions':8,'running':True,'sealed_auxiliary_contract_available':5,'sealed_auxiliary_contract_failures':4,
  'semantic_labelled_candidates':10,'candidate18_definite_boundary_error':'Exact total3 from merely visible1/2/3 plus arrows; judge reason only supports at least3.',
  'candidate18_labels':str(labels),'candidate18_labels_sha256':sha(labels),
  'candidate18_private_join':str(GUI/'reviewed-candidate-outcome-joins/1794206775289559700-5d679b2784bcfc1cfe22/join.json'),
  'candidate18_executed':False,'candidate18_rejection_reason':'Strict independent point containment, not correct detection of total-count overclaim.',
  'candidate16_appearance_absence_unresolved':True},
 'current_condition_fidelity_failure':{'diagnostic':str(diag),'sha256':sha(diag),
  'empty_text_refs_generation_constraint_not_actually_enforced':True,
  'cause':'Primary dependency restore caches canonical unpatched grammar ahead of auxiliary private vendor.',
  'strict_final_validator_unchanged':True,'invalid_readings_delivered_as_unavailable':True,
  'structurally_valid_wrong_text_associations_can_still_pass_final_schema':True,
  'next_linked_private_grammar_CPU_admission':str(admit),'next_admission_sha256':sha(admit),
  'private_namespace_and_escape_branch_repair_CPU_only':True,'live_runtime_modified':False},
 'user_stateless_requirement':{'contract':str(HERE/'contract.json'),'contract_sha256':sha(HERE/'contract.json'),
  'actual_one_image_one_prompt_forward_input_audit':str(actual_input),'audit_sha256':sha(actual_input),
  'actual_auxiliary_inputs_audited':9,'contextual_input_leak_observed':False,
  'old_Controller_same_image_reply_reuse_present':True,'next_source_removes_reply_memoization':True,
  'native_GPU_first_forward_empty_cache_and_post_call_context_clear_pending':True,
  'main_history_kept_and_receipts_preserved':True},
 'goal':'active','efficacy_proven':False,'no_general_rate_or_reduction_claim':True,
 'new_diagnostic_or_preparation_model_HTTP_GUI_calls':0,'old_completed_runs_and_queues_must_not_restart':True,
 'only_owned_physical_3090_GPUs':[4,5,6,7],
 'snapshots_are_not_current_process_authority':True}
def save(p,v):
 with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
save(out/'receipt.json',value)
head='''## 最新：2026-11-09 单图无上下文边界已确认；当前GUI继续，辅助约束部署故障已定位

权威为 `full-gui-bounded-evidence-20261109-03/'''+out.name+'''/receipt.json`、其中实际进程/9锁/原请求/事件链回执，以及 `stateless-auxiliary-20261109-07/contract.json`。用户最新明确：唯一辅助每次只接收实际一张完整当前供应图＋固定通用prompt，独立调用，输出后丢弃当次运行上下文；不输入任务/主历史/候选/目标/上一轮辅助内容。主模型保留自己的完整合法历史，原始实验回执不删除。权重与只读词表可常驻。新源码已去掉Controller同图回复memoization，保留60辅助cap；CPU模拟正反边界通过，实际GPU空past和清理钩子尚待新条件验证，不能称已部署。

已核9条真实辅助请求的完整原图/固定提示和native CPU重建输入，逐项等于真实首forward IDs/pixels/grid；0任务历史泄露。旧审计未记录past KV，不能把输入隔离直接称实际KV空状态已验证。旧冻结运行仍有同图回复复用，不等同辅助对话累积；不热改当前条件。

重要纠正旧头“mask强制text_refs=[]”：生产主依赖恢复覆盖并缓存了canonical旧lmformatenforcer，实际辅助没有用补丁vendor。封存0051输出CPU按实际导入顺序重放全部token被允许，私有alias在token346拒绝非空引用；无新推理。5已封存辅助完整SHA保全。新独立namespace修复保留主模块对象/文件；新增escaped-Unicode CPU失败也已保全，新linked02仅私有token缓存补backslash分支后原生控制通过。原validator/原始输出未编辑，过长字串和读图错误仍可能拒绝或出错；新GPU推理/主Controller效果未验证。

实际快照105模型尝试：首clean无辅助终局10actor+39judge=49EOS，6动作/官方0，regeneration_cap，原1056请求文件/49跨端绑定/33GUI文件审计完成，严禁重跑。全10候选已审：0确定正例但1唯一性子断言未决，所以轨迹Mirage未知，不能说无Mirage。第二clean单辅助快照11actor/36judge尝试/9辅助、8动作仍运行；9辅助5契约可用/4拒绝，不是5语义通过。已源优先封存前20候选：c18把可见1/2/3加next/last当总共3页，核验理由仅支持至少3却称supported；原点位在page2内，另一个点读错导致严格拒绝，未执行，不能说计数防御成功。c16西装排除仍未决。后续更正不抹去已发生的候选错误，不能估计降幅。

worker3959659 UID1033/start1182249260与GUI2380246 UID1015/start118691319仅定位；后续须重核实际完整cmd/锁/日志/原请求回复与SHA链，禁止health/重复submit/旧queue。新alias、无上下文清理、正常探索误拦与点读修复在独立新attempt准备；不可改冻结运行、强行通过或补花已完成失败预算。独立8任务准备仍launch_ready=false。用户目标ACTIVE，尚无防御有效证据。

'''
for name in ['HANDOFF.md','README.md']:
 p=BASE/name;raw=p.read_bytes();(out/(name+'.before')).write_bytes(raw)
 assert p.read_bytes()==raw
 p.write_text(head+raw.decode('utf8'),encoding='utf8')
current=BASE/'full-gui-current.json'
(out/'prior-full-gui-current.json').write_bytes(current.read_bytes())
current.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
print(json.dumps({'receipt':str(out/'receipt.json'),'sha256':sha(out/'receipt.json'),
 'goal':'active','efficacy_proven':False,'new_model_GUI_calls':0}))
