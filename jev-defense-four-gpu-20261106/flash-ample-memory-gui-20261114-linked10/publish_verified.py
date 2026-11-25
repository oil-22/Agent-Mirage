"""Publish only independently verified capacity, actual GUI work and immutable receipts."""
import base64,hashlib,io,json,time,zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from control import HERE,BASE,R3090,R4090,save,sha,remote
def newest(pattern):return max(HERE.glob(pattern),key=lambda p:p.stat().st_mtime_ns)
def load(p):return json.loads(p.read_bytes())
rp=newest('ready-audit-*.json');ready=load(rp)['result']
ld=newest('live-evidence-*');live=load(ld/'summary.json');tp=newest('terminal-audit-*.json');terms=load(tp)['result'];fp=newest('Flash-live-audit-*.json');flash=load(fp)['result']
assert ready['minimum_reserved_peak_headroom_GiB']>=3
assert live['verified_main_replies']>0 and live['verified_Flash_replies']>0 and live['environment_action_events']>0
assert load(HERE/'GUI-submission.json')['result']['expected_trajectories']==29
ts=time.time_ns();pub=HERE/('verified-publication-'+str(ts));pub.mkdir();stamp=datetime.fromtimestamp(ts/1e9,timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S +08:00')
old={n:(BASE/n).read_bytes()for n in ['HANDOFF.md','README.md']}
for n,b in old.items():(pub/('prior-parent-'+n)).write_bytes(b)
if(HERE/'experiment-current.json').exists():(pub/'prior-experiment-current.json').write_bytes((HERE/'experiment-current.json').read_bytes())
frozen=load(HERE/'frozen-package.json');plan=load(HERE/'package/plan.json');cap=ready['capacity'];terminal=terms['terminals'];good=[v for v in terminal if not v['infrastructure_failure']]
status={'time':ts/1e9,'evidence_time':stamp,'goal':'active','attempt':HERE.name,'expected_new_GUI':29,'old_terminals_preserved':{'normal':2,'OOM':1,'reexecuted':False},'new_complete_pair_plan':{'tasks':7,'pairs':14,'T000_stale_gate_is_unpaired_diagnostic':True,'old_three_card_pair_not_pooled':True},'frozen':frozen,'capacity_audit':str(rp),'capacity':cap,'minimum_reserved_peak_headroom_GiB':ready['minimum_reserved_peak_headroom_GiB'],'CUDA_scheduling':'primary CUDA_LAUNCH_BLOCKING=1, no forward empty_cache; Flash native scheduling unchanged; both formal arms identical','explicit_placement':plan['placement'],'live_audit':live,'live_audit_source':str(ld),'terminal_audit':str(tp),'terminals':terminal,'completed_non_infrastructure':len(good),'infrastructure_terminals':len(terminal)-len(good),'current_GUI_snapshot':terms['batch_status_snapshot'],'Flash_CPU_full_tensor_probability_audit':str(fp),'Flash_replies_CPU_verified':flash['verified_complete_Flash_replies'],'semantic_review_complete':False,'Mirage_reduction':None,'defense_effectiveness_proven':False,'new_model_GUI_calls_by_publication':0}
status['native_allocator_memory_fraction']=0.85;status['unused_cache_GC_threshold']=0.8
save(pub/'status.json',status)
for source,name in [(rp,'capacity-audit.json'),(ld/'summary.json','live-audit.json'),(tp,'terminal-audit.json'),(fp,'Flash-CPU-audit.json'),(HERE/'README.md','runtime-README.md')]:
 (pub/name).write_bytes(source.read_bytes())
memrows='\n'.join(f"| {v['physical_gpu']} | {v['peak_reserved_bytes']/1024**3:.2f} | {v['headroom_at_reserved_peak_bytes']/1024**3:.2f} |"for v in cap['probes'][0]['memory'])
trows='\n'.join(f"| {v['run']['run_id']} | {v['actor_calls']} | {v['Flash_replies']} | {v['environment_actions']} | {v['outcome']} | {v['official_reward']} |"for v in terminal)or'| 暂无已封终局 | — | — | — | — | — |'
report=f'''# 充裕显存下的Flash完整GUI实验进展

截至北京时间 **{stamp}**，`{HERE.name}` 已在3090实际启动完整GUI：主27B使用物理0–6，Flash独占7。已有真实主回复、Flash请求与原生环境动作，实际UID/完整命令/start/UUID及主17锁、Flash9锁已独立核对。冻结{frozen['files']}文件manifest：`{frozen['manifest_sha256']}`。

只续跑29条此前未开始轨迹，原2个正常终局和1个OOM技术终局不重跑。新七任务形成14完整配对（正常/一次旧帧×无门控/Flash）；T000旧帧门控单列诊断，旧三卡正常配对不混入新七卡分母。目前已封存{len(good)}/29个非基础设施终局，{len(terminal)-len(good)}个基础设施终局。读取快照：`{terms['batch_status_snapshot']}`。

## 容量与数值准入

依据1184个实际state tensor大小显式连续分配完整decoder blocks，视觉+embedding在0，64层分到1–6，norm/lm_head在6；全部1187真实parameters/buffers严格CUDA，BF16/SDPA，无CPU/disk模型offload、无根dispatch钩子。nonpersistent静态buffer只按明确模块CUDA位置放置，完整字节与dtype核对。

内存修复复用三个chunk私有死点乘结果缓冲及MLP死SiLU缓冲，保留head形状、矩阵乘、规约、元素操作数顺序与精度；仅在精确恢复三个输出目的表达式并去掉del后，chunk AST与原式相等，不声称原AST未改。主CUDA同步执行、forward内不清allocator缓存；Flash调度保持原状，同步可能增加延迟，两正式臂相同。未修改pinned库源码。

9项CPU/GPU完整chunk输出及状态、12项各卡实际MLP权重输出字节与输入未改检查通过；真实15图15367tokens连续3步全词表logits/IDs逐位一致，每遍48chunk/192MLP调用。3token工程cap不是EOS。新合成50图53167tokens完整自然EOS、全部126输出IDs等于封存linked02结果，**每卡reserved峰值余量至少{ready['minimum_reserved_peak_headroom_GiB']:.2f}GiB**。50图是标明合成重复历史，不是50步GUI，不保证所有未来历史/每步2048输出最坏容量或普遍逐位相同。

| 物理3090 | 峰值reserved GiB | 峰值余量GiB |
|---|---:|---:|
{memrows}

此前各独立内存attempt全部保全，不重跑：原七卡50图OOM；linked02余量不足；linked03 head分组逐位失败；linked04 IDs一致但余量不足；linked05自动分配尾卡过重OOM；linked06遗漏nonpersistent缓冲被严格设备审核拒绝；linked07根钩子导致GPU0加载OOM；linked08修复后CUDA非法访存，未通过全模型比较。不能把技术故障当模型零分，也不能仅凭当前通过就断言原非法访存的单一根因。成本须单列这些工程检查与八卡实际保留时间、峰值和延迟，不编造货币/能耗或成本降低。

## 已验证的实际调用

独立快照逐文件核对{live['verified_main_replies']}份完整主回复、{live['verified_Flash_replies']}份Flash回复、{live['environment_action_events']}个环境动作事件、{live['YES_forwarded_bindings_verified']}组YES原图转交和{live['actual_main_input_image_bindings_verified']}组主模型实际图片绑定。完整wire/接受历史/实际first-forward IDs,pixels,grid/有效生成参数/输出IDs,EOS/原回复/request-reply seals及事件链通过。另CPU重载核对{flash['verified_complete_Flash_replies']}份实际Flash张量并重建原始head概率，0额外推理或GPU分配。快照之后的调用不追溯混入这些数字。

| 新轨迹 | actor | Flash | 实执动作 | 终止 | 官方分数 |
|---|---:|---:|---:|---|---:|
{trows}

## 保持的框架与效果边界

Flash固定revision `9ff7cf9838e59df461c276b7699d56b244d2af58`，每次仅完整单图+固定通用问题，无任务/主历史/候选/前图/累积KV。YES同PNG送主模型，不附加辅助文字/概率；NO等待0.5秒，持续同环境新复拍至YES或手停。技术故障保全后停，不当NO。主完整接受历史、原图、BF16/SDPA、原生提示/解析/执行/评分、2048输出、50决策70actor和原seed保持，无旧上下文语义judge，网站不重置、私有答案不入模型。

单图不能证明清晰旧帧新鲜，也不证明动作正确。语义审查未完成、Mirage降幅null，**尚未证明防御有效**。后续按完整配对的原图和合法历史审查边界包含Mirage、放行/实执错误、正常操作误拦/等待、官方完成与技术故障；纠正不抹去发生、纯nativeWAIT排除、未知保持未知。不能用一直等待、少行动、全YES、评分或挑阳性宣称有效。目标保持active，所有旧队列不恢复。

手停：创建 `{R4090}/STOP`，在途调用结束后停止后续转交与动作。
'''
mlp_tests=ready['lifetime_proof']['MLP_memory_proof']['actual_weight_GPU_output_bitwise_tests']
report=report.replace('12项',str(mlp_tests)+'项').replace('64层分到1–6','64层分到0–6')
report=report.replace('## 已验证的实际调用','linked09已完整通过上述数值检查和50图126IDs，但峰值reserved余量仅1.62GiB，157文件封存。本linked10让所有七张主GPU承担decoder blocks，并将原生allocator限制为物理内存0.85、闲置缓存GC阈值0.8；只回收未使用缓存，不截断/缩图/降精度，可能增加分配延迟或拒绝更大未来live工作集，两正式臂相同。实际峰值与EOS证据见上表，不能仅从预算设置称容量成功。\n\n## 已验证的实际调用')
name='Flash七卡充裕显存与完整GUI进展-20261114.md';(pub/name).write_text(report,encoding='utf8');save(pub/'publication-seal.json',{p.name:sha(p)for p in pub.iterdir()if p.is_file()})
pointer={'publication':str(pub),'status':str(pub/'status.json'),'status_sha256':sha(pub/'status.json'),'report':str(pub/name),'report_sha256':sha(pub/name),'publication_seal_sha256':sha(pub/'publication-seal.json'),'goal':'active','Mirage_reduction':None,'time':ts/1e9}
tmp=HERE/('.pointer-'+str(ts)+'.json');save(tmp,pointer);tmp.replace(HERE/'experiment-current.json')
head=f'''## 最新：2026-11-14 {HERE.name}充裕显存准入通过，29条完整GUI已实际续跑

权威 `{HERE.name}/experiment-current.json` → `{pub.name}/status.json` 和 `{name}`。截至{stamp}，实际主3090物理0–6/Flash7，完整GUI已有{live['verified_main_replies']}份主回复/{live['verified_Flash_replies']}Flash/{live['environment_action_events']}实执事件的SHA/链及实际输入核验，新非基础设施终局{len(good)}/29、技术终局{len(terminal)-len(good)}。主17锁/Flash9锁、UID/fullcmd/start/UUID已核。不要重复stage/service/gui；原2正常+1OOM终局及所有旧队列不重跑。新七任务14完整配对，T000旧帧门控单列诊断，旧三卡对照不池化。

source-bound显式完整层分配、无根钩子、1187实际参数/buffer严格CUDA；原图/完整接受历史/BF16/SDPA/原生提示解析执行评分/2048输出/50决策70actor/seed保持。三个chunk死点乘缓冲及MLP死SiLU缓冲复用；精确恢复原目的表达式并去del后AST相同，不称原AST未改。主CUDA_LAUNCH_BLOCKING=1、无forward清allocator，Flash原调度；同步延迟单列，双臂同版。9chunk＋12实际MLP输出/状态字节及输入未改、15图连续3步全词表logits/IDs逐位、50图53167tokens自然EOS全部126IDs等于linked02；各卡reserved峰值余量最小{ready['minimum_reserved_peak_headroom_GiB']:.2f}GiB。容量压力是合成，不保证任意最坏历史/普遍数值同一。manifest `{frozen['manifest_sha256']}`，{frozen['files']}冻结源文件不可热改。

全部此前内存技术attempt保留，原illegal memory根因不能仅凭新通过定论；技术失败不是语义零分。Flash仍独立单完整图固定通用问、无任务/主上下文/候选/前图/KV；YES同PNG转主无附文，NO0.5秒同环境持续新复拍到YES或手停，技术失败不是NO。单图不证明清晰旧帧新鲜或动作正确。语义审查未完成、Mirage降幅null、效果未证明，目标active；后续审错误/误拦/等待/官方完成，未知不当无Mirage，纠正不抹去发生。以下旧头仅历史。

'''
head=head.replace('12实际MLP',str(mlp_tests)+'实际MLP').replace('64层分到1–6','64层分到0–6')
head=head.replace('以下旧头仅历史。','linked09全部数值与50图126IDs一致但余量不足/157文件保留；linked10全部七卡承担decoder blocks、allocator物理比例0.85与闲置缓存GC0.8，实际EOS与峰值准入通过，可能增加分配延迟或拒绝更大未来live集合，两正式臂相同。以下旧头仅历史。')
for n,b in old.items():assert(BASE/n).read_bytes()==b;(BASE/n).write_bytes(head.encode('utf8')+b)
payload=io.BytesIO();names=['status.json',name,'runtime-README.md','capacity-audit.json','live-audit.json','terminal-audit.json','Flash-CPU-audit.json']
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED)as z:
 for n in names:z.writestr(n,(pub/n).read_bytes())
 z.writestr('experiment-current.json',(HERE/'experiment-current.json').read_bytes())
with zipfile.ZipFile(io.BytesIO(payload.getvalue()))as z:expected={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}
deliveries=[]
for host,root in [('3090',R3090),('4090',R4090)]:
 code='ROOT='+repr(root)+'\nPUB='+repr(pub.name)+'\nEXPECTED='+repr(expected)+'\n'+r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
r=Path(ROOT)/'documentation'/PUB;r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():
  p=r/n;assert p.resolve().is_relative_to(r.resolve())
  with p.open('xb')as f:f.write(z.read(n))
for n,h in EXPECTED.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
out={'root':str(r),'files_verified':len(EXPECTED),'runtime_sources_changed':False,'new_model_GUI_calls':0}
with(r/'delivery-receipt.json').open('x')as f:json.dump(out,f,indent=2)
print(json.dumps(out))
'''
 raw,op=remote(host,code,'deliver-verified-actual-GUI-publication-'+host,private_prefix='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n');deliveries.append({'host':host,'result':json.loads(raw),'operation':str(op)})
save(HERE/('publication-created-'+str(ts)+'.json'),{'pointer':pointer,'deliveries':deliveries});print(json.dumps({'report':str(pub/name),'current':str(HERE/'experiment-current.json'),'completed':len(good),'expected':29,'goal':'active'},ensure_ascii=False))
