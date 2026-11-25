"""Publish already-running experiment evidence without changing frozen runtime files."""
import base64,hashlib,io,json,time,zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from control import HERE,BASE,R3090,R4090,remote,save,sha

EXPECTED='090740a313e2b9c74563a197dcd0746819c4b079d06b844438ccaba8aba47ef1'
assert sha(HERE/'package-linked02/manifest.json')==EXPECTED
assert not(HERE/'experiment-current.json').exists(),'Publication exists; inspect instead of repeating.'
evidence=max(HERE.glob('live-evidence-*'),key=lambda p:p.stat().st_mtime_ns)
for name,h in json.loads((evidence/'seal.json').read_bytes()).items():assert sha(evidence/name)==h
live=json.loads((evidence/'summary.json').read_bytes())
main=json.loads((evidence/'3090.json').read_bytes())
terminalpath=max(HERE.glob('terminal-audit-*.json'),key=lambda p:p.stat().st_mtime_ns)
term=json.loads(terminalpath.read_bytes())
flashpath=max(HERE.glob('Flash-live-audit-*.json'),key=lambda p:p.stat().st_mtime_ns)
flash=json.loads(flashpath.read_bytes())
plan=json.loads((HERE/'package-linked02/plan.json').read_bytes())
assert len(plan['queue'])==32 and len(plan['tasks'])==8
assert term['result']['batch_status_snapshot']['phase']=='running'
completed=term['result']['batch_status_snapshot']['completed']
ts=time.time_ns();pub=HERE/('startup-publication-'+str(ts));pub.mkdir()
stamp=datetime.fromtimestamp(term['result']['time'],timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S +08:00')
for name in ['HANDOFF.md','README.md']:(pub/('prior-parent-'+name)).write_bytes((BASE/name).read_bytes())
(pub/'experiment-README.md').write_bytes((HERE/'README.md').read_bytes())
for src,name in [(evidence/'summary.json','live-summary.json'),(terminalpath,'terminal-audit.json'),(flashpath,'Flash-live-CPU-audit.json')]:
 (pub/name).write_bytes(src.read_bytes())
status={
 'kind':'actual-full-GUI-startup-and-first-sealed-terminals',
 'created':ts/1e9,'evidence_read_time_local':stamp,
 'user_request':'启动完整的实验',
 'phase_at_last_terminal_inspection':'running','expected_trajectories':32,
 'tasks':8,'matched_pairs':16,'conditions':['clean','one-shot-stale-replacement'],
 'arms':['native-primary-without-gate','single-image-Flash-YES-NO-gate'],
 'completed_non_infrastructure_trajectories_at_inspection':completed,
 'current_GUI_snapshot':term['result']['batch_status_snapshot'],
 'sealed_terminal_results':term['result']['terminals'],
 'frozen_package':str(HERE/'package-linked02'),'manifest_sha256':EXPECTED,
 'actual_live_audit':{'source':str(evidence),'verified_main_replies':live['verified_main_replies'],'verified_Flash_replies':live['verified_Flash_replies'],'YES_image_bindings':live['YES_forwarded_bindings_verified'],'actual_main_input_image_bindings':live['actual_main_input_image_bindings_verified'],'native_environment_action_events':live['environment_action_events'],'main_chain':live['main_chain'],'Flash_chain':live['Flash_chain'],'actual_processes':live['actual_processes']},
 'Flash_full_tensor_and_raw_head_CPU_audit':{'source':str(flashpath),'verified_complete_replies':flash['result']['verified_complete_Flash_replies'],'new_inference_by_audit':0,'GPU_allocations_by_audit':0},
 'model_placement':{'3090_physical_4_5_6':'original-27B-BF16-SDPA-balanced-22GiB-each','3090_physical_7':'pplx-decider-flash-v1.2-pinned-native-GPU-environment','compared_with_history':'New three-card primary placement; full history retained; no bitwise equivalence or future fit claim'},
 'Flash_revision':'9ff7cf9838e59df461c276b7699d56b244d2af58',
 'Flash_context':'One complete image plus fixed generic usability question; no task/history/candidate/prior images or cache accumulation',
 'NO_policy':'0.5-second pause; same-live recapture until YES or manual stop; no auxiliary-call or recapture cap',
 'YES_policy':'Forward exactly the same PNG bytes; no auxiliary text or scores added to original actor',
 'main_protocol':{'max_decisions':50,'max_actor_calls':70,'actor_max_new_tokens':2048,'actor_seed':42,'environment_seed':20261011,'full_accepted_history':True,'native_parser_executor_scorer_unchanged':True,'contextual_semantic_judge':False},
 'stale_injection':'One first changed post-action frame replaced by last actually main-delivered frame; fresh same-live recaptures are not reinjected',
 'technical_failure_policy':'Preserve and stop queue, without automatic retry/input reduction/precision change',
 'native_action_contract_failure_policy':'Seal that trajectory and continue the next independent unstarted trajectory',
 'semantic_labels_complete':False,'Mirage_reduction':None,'defense_effectiveness_proven':False,
 'old_queues_resumed':False,'new_model_GUI_calls_by_publication':0,
 'local_README':str(HERE/'README.md'),'remote_code_3090':R3090,'remote_GUI_4090':R4090,
}
save(pub/'status.json',status)
rows=[]
for t in term['result']['terminals']:
 rows.append(f"| {t['run']['run_id']} | {t['actor_calls']} | {t['Flash_replies']} | {t['environment_actions']} | {t['outcome']} | {t['official_reward']:g} | {t['sealed_files_verified']} |")
report=f'''# Flash 单图门控完整 GUI 实验已启动

截至北京时间 **{stamp}**，本轮32条完整GUI中已有 **{completed}/32条** 正常封存，队列正在执行 `{status['current_GUI_snapshot']['run_id']}`。原27B已产生真实回复，原生浏览器已执行动作；这份记录确认实际启动，不以提交或ready标志代替运行证据。

本轮是8个既定公开VWA classifieds任务（0、3、17、58、89、94、114、125）× 正常/一次旧帧条件 × 无门控/Flash门控两臂，共16个匹配对。所有轨迹使用新命名空间，旧终局和旧队列不重跑。任务为已选开发样本，32条不等于32个独立任务。

## 已完成的轨迹

| 轨迹 | 主模型回复 | Flash回复 | 实际环境动作 | 终止方式 | 官方分数 | 已核终局文件 |
|---|---:|---:|---:|---|---:|---:|
{chr(10).join(rows)}

首个正常条件匹配对两臂均由模型主动STOP，官方分数均为0，无基础设施失败、无复拍。该结果表示这两条未完成官方任务；尚未做逐候选Mirage语义审查，不能把分数0当成Mirage标签，也不能据此估计门控降低比例。

## 实际接线与条件

Flash固定版本 `perplexity-ai/pplx-decider-flash-v1.2` / `9ff7cf9838e59df461c276b7699d56b244d2af58`。每次只收到完整当前图和固定通用可观察性问题，不收到任务、主历史、候选、前图或门控历史，原生 `use_cache=false`。YES图字节原样送给主模型；NO等待0.5秒后从同一实时环境复拍，按用户选择持续到YES或手动停止。技术故障保留并停止，不当作NO。

YES仅表示当前可见界面连贯、可供观察。正常页脚、无结果页、可读弹窗等可以通过；空白、替代主界面的明确加载、严重损坏或无法辨认的图像应拒绝。单图不能保证识别清晰旧帧，也不证明动作正确。主模型不接收辅助解释、概率或摘要，本轮没有旧上下文语义judge。

主27B位于3090物理4–6卡，BF16/SDPA、balanced、每卡22GiB；Flash独占7卡。实际主模型1184份state tensors共54,713,457,120字节，位于逻辑CUDA0/1/2，没有模型CPU/disk offload。与历史四卡主模型部署不同，这是新三卡部署条件，两臂一致；不假定与旧部署逐位相同，也不保证后续长历史一定适配显存。

主模型保留全部实际接受的历史和原图，2048输出、50决策/70次actor上限及原seed。原生parser、executor、scorer与固定来源SHA绑定。旧帧仅在首次动作后完整图变化时替换一次，使用上次实际送主模型的图；NO后的复拍不重复注入、不滚动、不导航、不重置。私有评分答案不进入模型。模型/网络/资源/scorer技术失败封存并停队列，不自动重试或减小输入；原生动作格式错误封存当前轨迹后进入下一条独立轨迹。

## 核验依据

独立实时快照已逐文件核对 **{live['verified_main_replies']}份完整主回复、{live['verified_Flash_replies']}份Flash回复、{live['environment_action_events']}个实际环境动作事件**，核实{live['YES_forwarded_bindings_verified']}组YES图片转交与{live['actual_main_input_image_bindings_verified']}组主模型真实输入图片绑定。这些是读取时的完整记录下界，后续调用不混入该快照。完整主历史前缀、首forward IDs/pixels/grid、生成参数、原始输出IDs/EOS、request/reply seals、事件链均已绑定。另一次CPU审计重载8份实际Flash输入张量并重建原始head及概率绑定，未产生新推理/GPU分配。

实时核验确认主模型和Flash实际UID1033、完整命令/start ticks及九继承锁，GUI UID1015，实际GPU UUID/进程与授权4–7卡一致。仅核验和使用已授权资源，网站未重置/导入。冻结54文件包manifest SHA：`{EXPECTED}`。旧standalone Flash4回复先封存再正常停止，64个postexit文件通过，新服务不重跑旧控制。

主要证据位置：

- 实时核验：`{evidence}`
- 首对终局与完整seal：`{terminalpath}`
- Flash实际张量与原始概率CPU审计：`{flashpath}`
- 3090原始请求：`/data/researcher/jev-defense-four-gpu-20261106/flash-gated-full-gui-20261113/primary/requests`
- 4090截图/完整历史/原生动作/评分：`{R4090}/batch/runs`

最终效果需要按完整合法历史和原图审查首次错误、放行/实际执行、正常操作误拦、任务完成及复拍成本。发生后纠正仍计数，纯原生WAIT排除。当前Mirage标签及相对降幅均为null，尚未证明防御有效。

手动停止可创建 `{R4090}/STOP`，或向核实身份后的GUI runner发SIGINT/SIGTERM/SIGUSR1。在途调用返回后会停止后续转交和动作，已经派发的动作无法撤回。不要再次运行stage/retire/service/gui入口。
'''
report_name='Flash单图门控完整GUI实验启动-20261113.md'
(pub/report_name).write_text(report,encoding='utf8')
save(pub/'publication-seal.json',{str(p.relative_to(pub)):sha(p)for p in pub.iterdir()if p.is_file()})
pointer={'publication':str(pub),'status':str(pub/'status.json'),'status_sha256':sha(pub/'status.json'),'report':str(pub/report_name),'report_sha256':sha(pub/report_name),'publication_seal_sha256':sha(pub/'publication-seal.json'),'frozen_manifest_sha256':EXPECTED,'phase_at_evidence_time':'running','completed_at_evidence_time':completed,'expected':32,'Mirage_reduction':None,'created':ts/1e9}
save(HERE/'experiment-current.json',pointer)
head=f'''## 最新：2026-11-13 用户已启动新的Flash单图门控完整GUI；{completed}/32终局已封，旧队列不恢复

最新权威 `flash-gated-full-gui-20261113/experiment-current.json` → `{pub.name}/status.json` 和 `Flash单图门控完整GUI实验启动-20261113.md`。用户最新明确“启动完整的实验”，本轮32新轨迹/8任务/16配对（正常与一次旧帧×无门控与Flash门控）已实际执行，覆盖旧头“仅Flash部署/GUI暂停”。截至{stamp}已封{completed}/32，无基础设施失败，当前 `{status['current_GUI_snapshot']['run_id']}`；首个T000正常条件对两臂各8actor/7环境实执，门控臂8Flash全YES、0复拍，两臂model_stop且官方0；语义Mirage标签和降低比例仍null，不据此宣称防御有效。

54冻结文件manifest `{EXPECTED}`，新3090主27B UID1033/PID1314802和Flash UID1033/PID1314216仅供定位；管理前重核完整命令/start、九继承锁/UUID/实际请求。主模型物理4–6三卡balanced/BF16/SDPA，Flash独占7；新部署两臂一致，与历史四卡主模型不同，不宣称输出逐位或长历史显存保证。主完整接受历史/图、2048输出、50决策/70actor/seed、原生parser/executor/scorer保持；无旧上下文语义judge、无辅助摘要/概率注入。私有答案不进输入，网站未重置。

Flash单次完整单图+固定通用问题，没有任务/主历史/候选/前图/累积KV；YES原PNG转交，NO按用户采用0.5秒持续同环境复拍到YES或手停，无2复拍/60辅助上限。单图不证明清晰旧帧新鲜性/动作正确。核验快照已绑定15完整主回复、8Flash、14环境动作事件、8YES图片和15实际主输入，另8份Flash实际张量/原始head概率CPU审计完成。终局seal/事件链通过。技术失败封存后停队列，不自动重试/缩图/减历史/改精度；原生动作格式终局不重跑。手动STOP路径与报告一致。不要再次运行stage/retire/service/gui入口，不恢复旧attention/UI-TARS/VWA20等队列。

原standalone Flash4次回复与64 postexit文件已封后正常停止，旧PID1305138和旧deployment-current仅历史；新服务真实GUI请求在新目录。此前终局、旧32/28轨、旧54比较控制均保留不重跑。完整实验尚未完成。以下旧头仅保留历史。

'''
for name in ['HANDOFF.md','README.md']:
 old=(pub/('prior-parent-'+name)).read_bytes()
 assert(BASE/name).read_bytes()==old,'Parent changed during publication; do not overwrite.'
 (BASE/name).write_bytes(head.encode('utf8')+old)
save(HERE/('startup-created-'+str(ts)+'.json'),pointer)

# Documentation only. Never replace a frozen source, token, request or terminal.
payload=io.BytesIO()
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
 for name in ['status.json',report_name,'experiment-README.md','live-summary.json','terminal-audit.json','Flash-live-CPU-audit.json']:
  z.writestr(name,(pub/name).read_bytes())
 z.writestr('experiment-current.json',(HERE/'experiment-current.json').read_bytes())
docfiles={}
with zipfile.ZipFile(io.BytesIO(payload.getvalue()))as z:
 for name in z.namelist():docfiles[name]=hashlib.sha256(z.read(name)).hexdigest()
delivery=[]
for host,root in [('3090',R3090),('4090',R4090)]:
 code='ROOT='+repr(root)+'\nPUB='+repr(pub.name)+'\nEXPECTED='+repr(docfiles)+'\n'+r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
root=Path(ROOT)/'documentation'/PUB;root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as z:
 for name in z.namelist():
  p=root/name;assert p.resolve().is_relative_to(root.resolve())
  with p.open('xb')as f:f.write(z.read(name))
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==h for name,h in EXPECTED.items())
result={'root':str(root),'verified_files':EXPECTED,'runtime_sources_changed':False,'new_model_GUI_calls':0}
with(root/'delivery-receipt.json').open('x')as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result))
'''
 raw,op=remote(host,code,'deliver-startup-documentation-'+host,private_prefix='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n')
 delivery.append({'host':host,'result':json.loads(raw),'operation':str(op)})
save(HERE/('documentation-delivery-'+str(ts)+'.json'),delivery)
print(json.dumps({'current':str(HERE/'experiment-current.json'),'report':str(pub/report_name),'completed_at_evidence_time':completed,'expected':32,'delivery_hosts':[d['host']for d in delivery],'new_model_GUI_calls':0},ensure_ascii=False))
