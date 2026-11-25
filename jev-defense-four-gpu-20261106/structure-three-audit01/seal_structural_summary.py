"""Join completed immutable read-only audits locally; no remote calls."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
S=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
R=H/'service-audit-public-1794040226300580000'
C=H/'controller-audit-public-1794041050905022800'
P=B/'three-terminal-postexit-public/1794040388947724400'
M=H/'service-postexit-meta-1794041033962833500'
def load(p):return json.loads(p.read_bytes())
assert S(R/'receipt.json')=='ed32b419a92d671ffe2aebec0a69150ad8cf20b02bef407aa365bf78fcfcbff0'
assert S(R/'seal.json')=='dd11d1db5572f7613c006c7ac192ca7097572e878f265d9f3297dd468a218cac'
assert S(C/'audit.json')=='458dd8c85733ef6a52ec0ef1bc33741c608afe55b1484b5a3804378487f87bf7'
assert S(C/'seal.json')=='2ff8c651eaeb8cc3d469758999be705b106479a5d9ee59de62172c019d630519'
for name,h in load(R/'seal.json').items():assert S(R/name)==h
for name,h in load(M/'seal.json').items():assert S(M/name)==h
manifest=load(P/'public/terminal-sha256.json')
assert S(P/'public/terminal-sha256.json')=='0f84fcfe8a7d51d899f5d73966bf6bcff799c4507cb10f890304a960f2795a17'
meta=[]
for name,h in load(M/'seal.json').items():
    if name=='resource-lease.json':continue
    assert manifest[name]==h,name
    meta.append(name)
assert S(M/'online-admission.json')==manifest['online-admission.json']
s=load(R/'receipt.json');c=load(C/'audit.json');active=c['runs'][0]
assert s['status']=='passed_all_actual_requests_and_forwards'and c['integrity_audit_passed']
assert c['service_request_count']==s['request_count']==119
assert c['service_journal_chain_head']==s['service_journal_head']
out=H/'structural-summary-1794041050905022800';out.mkdir(exist_ok=False)
summary={
 'status':'passed_structural_and_provenance_audit_not_semantic_defense_success',
 'service_request_audit':{'path':str(R/'receipt.json'),'receipt_sha256':S(R/'receipt.json'),'seal_sha256':S(R/'seal.json')},
 'controller_audit':{'path':str(C/'audit.json'),'receipt_sha256':S(C/'audit.json'),'seal_sha256':S(C/'seal.json')},
 'original_exit_audit':{'path':str(P/'report.json'),'receipt_sha256':S(P/'report.json'),'seal_sha256':S(P/'seal.json'),'original_service_manifest_sha256':S(P/'public/terminal-sha256.json'),'actual_manifest_files':848},
 'actual_calls':s['request_totals'],'native_EOS_primary':97,'actual_auxiliary_forwards':20,
 'controller_events':active['event_count'],'controller_chain_head':active['event_chain_head'],
 'service_events':s['service_journal_events'],'service_chain_head':s['service_journal_head'],
 'actor_candidates':24,'actor_packets':24,'same_source_packet_reuses':4,'accepted_and_executed_environment_actions':19,
 'stale_control_runs_unstarted_zero_calls':2,'all_three_trajectories_complete':False,
 'service_metadata_bound_to_original_terminal_manifest':meta,
 'full_primary_actual_request_messages_and_native_IDs_bound':True,
 'all20_original_BF16_readout_native_CPU_softmax_answer_exact':True,
 'temperature':s['native_temperature'],
 'pixels_scope':'original received image bytes + full actual message SHA + actual forward pixel tensor shape/raw hash + input IDs/image_grid raw hashes; NOT independently rerunning image processor to reencode all pixels',
 'no_semantic_labels_or_efficacy_inferred':True,'no_new_model_GPU_GUI_health_scorer_calls':0,
 'audit_only_failed_attempt':'three-service-audit-source-1794040161772309449 omitted native describe dependency; immutable failure preserved; linked02 only extracted original describe; no model retry',
 'reservation':'physical 3090 GPUs4-7 task holder still holds actual locks at postexit audit; worker exit is not whole holder-reservation end; do not claim final task GPUh/currency/energy',
}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
report='''# 本轮完整性与溯源审查（2026-11-07）

结构审计通过；这项结论只证明本轮原始输入、实际调用、回复、动作记录和终局可相互核对，不证明防御成功或降低 Mirage 触发率。

本次 clean＋observer 已终局：24 次 actor、73 次 judge 均原生 EOS，20 次辅助模型实际 forward，2 次运行生命周期请求，共 119 个唯一请求。24 个 actor 候选、24 个观察包（4 次相同源回复复用）、19 次接受且执行的环境动作均准确关联。两个 stale 对照仍未启动、0 调用。

原 Controller 的 1103 条事件完整 SHA 链和服务侧 238 条 journal 完整 SHA 链全部通过，并逐个联结实际 wire、原始 response、请求 seal、actual forward 和最终清单。4090 原 control 6 项、batch 80 项清单全核；3090 原服务终局 848 项及实际两个 worker 的 exit0/0，由独立退出审计验证。technical-failure 的 24/73/20 调用、19 动作、50 步预算及运行条件与事件一致。主模型 2048/4096 输出预算未改变，97 条均非截断终局。

服务侧直接读取每个原始请求目录。逐项检查 actual forward 输入 IDs 与 generation IDs、完整实际模型 messages、原始图片 SHA、image_grid int64 原始字节 SHA。20 个辅助输入保持仅当前截图、固定 state 与三问，不含任务、历史或候选；20 份原 BF16 marker readout 原始字节 SHA 已核，并以原温度 1.5539092221462472、原 float32 softmax 和原 native answer 逐项重算，与原始回复完全一致。

范围限制：图像证据包括收到的原图、完整消息及 actual forward pixel tensor 的原始 shape/hash 绑定。此次没有重新运行图像处理器，不能称为对全部 pixel tensor 的独立再编码一致性验证。辅助概率重算一致也不表示模型判断正确，结构 PASS 与独立图片/历史语义审查必须分开。

Controller 阶段采用明确的 split audit：先在3090以原 auditor 的 native_forward 及协议函数核实所有真实服务目录，再在4090调用未改函数体的原 audit_attempt、join_service_journal；native_forward 在第二阶段仅复核已完成的同一 wire/payload/原始 response/seal 证书。没有用证书代替第一阶段的真实 forward 验证，也没有重新执行模型、GUI 或 scorer。

审计过程首个服务审计因抽取原协议函数时遗漏 describe 依赖而失败，原源文件和失败回执已保留；新 linked02 只补抽取原 describe，未重试模型。所有审计0新增模型/GPU推理/GUI/health/scorer调用，不修改原终局或 validator，不读取 PRIVATE 期待标签作为 checker 输入。

服务已按 root 写入的 marker 正常退出，退出和请求/源码稳定性已核。physical 3090 GPU4–7 的任务 holder 仍持锁，完整资源预留未结束，不能把 worker 退出时间充作全任务 reservation 结束，不能编造最终总 GPU 卡时、货币或能耗。

机器回执与完整 SHA 见同目录 summary.json；原 service / Controller 审计回执保持在各自不可变目录。
'''
(out/'结构与溯源完整审查-20261107.md').write_text(report,encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.name:S(p)for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(out),'summary_sha256':S(out/'summary.json'),'report_sha256':S(out/'结构与溯源完整审查-20261107.md'),'seal_sha256':S(out/'seal.json')},ensure_ascii=False))
