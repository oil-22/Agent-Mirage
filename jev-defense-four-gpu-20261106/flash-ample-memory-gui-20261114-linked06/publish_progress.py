"""Publish read-only verified progress and preserve every prior handoff byte."""
import base64,hashlib,io,json,time,zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from control import HERE,BASE,R3090,R4090,save,sha,remote
def latest(pattern):return max(HERE.glob(pattern),key=lambda p:p.stat().st_mtime_ns)
ready_path=latest('ready-audit-*.json');ready=json.loads(ready_path.read_bytes())['result']
live_dir=max(HERE.glob('live-evidence-*'),key=lambda p:p.stat().st_mtime_ns)
live=json.loads((live_dir/'summary.json').read_bytes())
terminal_path=latest('terminal-audit-*.json');terminal=json.loads(terminal_path.read_bytes())['result']
flash_path=latest('Flash-live-audit-*.json');flash=json.loads(flash_path.read_bytes())['result']
ts=time.time_ns();pub=HERE/('verified-publication-'+str(ts));pub.mkdir()
stamp=datetime.fromtimestamp(ts/1e9,timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S +08:00')
prior={}
for name in ['HANDOFF.md','README.md']:
 prior[name]=(BASE/name).read_bytes();(pub/('prior-parent-'+name)).write_bytes(prior[name])
if(HERE/'experiment-current.json').exists():(pub/'prior-experiment-current.json').write_bytes((HERE/'experiment-current.json').read_bytes())
cap=ready['capacity'];terms=terminal['terminals'];good=[t for t in terms if not t['infrastructure_failure']]
status={'kind':'verified-seven-GPU-full-history-Flash-GUI-continuation','evidence_time':stamp,'user_request':'按照充裕的显存预算跑起来，目标是跑出效果为止','goal':'active','expected_new_trajectories':29,'preserved_old_normal_terminals':2,'preserved_old_OOM_terminals':1,'old_terminals_reexecuted':False,'new_complete_paired_tasks':7,'planned_new_complete_pairs':14,'T000_stale_gate_unpaired_diagnostic':True,'manifest_sha256':ready['manifest_sha256'],'capacity_audit':str(ready_path),'minimum_reserved_peak_headroom_GiB':ready['minimum_reserved_peak_headroom_GiB'],'capacity_probes':cap,'model_placement':{'primary_physical_gpus':list(range(7)),'Flash_physical_gpu':7,'main_dtype':'BF16','attention':'SDPA','primary_actual_inherited_held_locks':17,'Flash_actual_inherited_held_locks':9},'actual_live_audit':live,'live_audit_source':str(live_dir),'terminal_audit_source':str(terminal_path),'terminal_results':terms,'completed_non_infrastructure':len(good),'infrastructure_terminals':len(terms)-len(good),'Flash_actual_tensor_probability_CPU_audit':str(flash_path),'Flash_replies_verified_by_CPU_audit':flash['verified_complete_Flash_replies'],'current_GUI_snapshot':terminal['batch_status_snapshot'],'semantic_review_complete':False,'Mirage_reduction':None,'defense_effectiveness_proven':False,'changed_gate_or_actor_conditions':False,'memory_repair':'Additional dead-local deletions only; original numerical AST/kernel/head shape/casts/order unchanged; no installed-source edit','new_model_GUI_calls_by_publication':0}
status['memory_repair']='Source-bound explicit placement of all1184 tensors; original head shape, matmul/reduction/operand order and precision retained. Three private dead pointwise buffers reused; explicit restoration to original expressions yields identical arithmetic AST. MLP buffer reuse and unused allocator-block purge. No pinned source edit; bitwise GPU and full-model controls required.'
status['model_placement']['explicit_placement']=json.loads((HERE/'package/explicit-placement.json').read_bytes())
save(pub/'status.json',status)
for src,name in [(ready_path,'capacity-audit.json'),(live_dir/'summary.json','live-audit.json'),(terminal_path,'terminal-audit.json'),(flash_path,'Flash-CPU-audit.json'),(HERE/'README.md','experiment-README.md')]:
 (pub/name).write_bytes(src.read_bytes())
table='\n'.join(f"| {t['run']['run_id']} | {t['actor_calls']} | {t['Flash_replies']} | {t['environment_actions']} | {t['outcome']} | {t['official_reward']} |"for t in terms)or'| 暂无已封终局 | — | — | — | — | — |'
memory='\n'.join(f"| {v['physical_gpu']} | {v['peak_reserved_bytes']/1024**3:.2f} | {v['headroom_at_reserved_peak_bytes']/1024**3:.2f} |"for v in cap['probes'][0]['memory'])
report=f'''# Flash完整GUI：七卡主模型、充裕显存验证与续跑

截至北京时间 **{stamp}**，已在3090物理0–6卡实际加载原27B，Flash独占7卡，完整GUI已产生真实主回复和原生环境动作。只继续29条此前未开始轨迹；原2个正常终局和1个OOM技术终局均保持原样。新轨迹中7任务构成14完整配对，T000旧帧门控单列诊断；不把原三卡对照混入新七卡效果分母。

## 显存修复及输出核验

原七卡实现可完整生成原15图15367tokens请求，但合成50图53167tokens在原生chunk delta临时张量处OOM；linked02仅释放已死局部引用后50图自然EOS126tokens，但最小峰值reserved余量0.84GiB，未通过3GiB准入。linked03的head分组未通过核逐位检查，已拒绝并封存，0正式GUI。

linked04仍未达到3GiB余量，完整50图EOS及全部126输出IDs相同，94文件已封存。linked05虽通过MLP与全模型逐位检查，但自动分配尾卡11.68GB权重，50图OOM，149文件已保全。当前linked06按封存1184个张量的大小，以CPU规划显式连续完整decoder映射：视觉+embedding0，64层分布1–6，norm/lm_head6。原head形状、matmul、规约、元素操作数顺序和精度保留；query标量、row广播、k_beta广播的三个乘法复用各自已死私有结果缓冲，逐项恢复原输出目的表达式并去掉del后，AST才与原式逐节点相等，不声称未经恢复的AST相同。MLP相同逐元素乘法写入已死SiLU输出，保留原gate/up/down与SiLU，输入/权重未改；长MLP前释放allocator未用缓存块，不修改pinned源码文件。实际各卡MLP权重1/65token完整输出字节相同、输入未改；9个chunk输出/状态相同；真实15图连续3步每遍192MLP/48chunk调用，全词表logits与IDs逐位一致。工程3-token cap不算正式EOS。两正式臂同一映射与内存处理。新50图完整生成与linked02全部126个输出IDs一致，**每卡reserved峰值余量至少{ready['minimum_reserved_peak_headroom_GiB']:.2f}GiB**。

| 物理3090卡 | 压力测试峰值reserved GiB | 峰值余量GiB |
|---|---:|---:|
{memory}

50图是标明的合成重复历史压力输入，不是实跑50步；不证明所有未来历史、每步2048tokens最坏情况都能适配，也不以有限逐位比较声称普遍输出一致。15图完整EOS复用，未重跑已完成整段控制。此前各个独立attempt的失败输入、原图、实际tensor、源码和日志及postexit seals均保留。

## 本轮实际进度

最近终局审计完成{len(good)}/29条非基础设施轨迹，基础设施终局{len(terms)-len(good)}。当前读取快照：`{terminal['batch_status_snapshot']}`。独立实查已核对{live['verified_main_replies']}个完整主回复、{live['verified_Flash_replies']}个Flash回复、{live['environment_action_events']}个环境动作事件；{live['YES_forwarded_bindings_verified']}组YES原图转交和{live['actual_main_input_image_bindings_verified']}组主模型实际输入图片绑定。以上是读取时已封证据下界，后续调用不追溯混入。

| 新轨迹 | actor | Flash | 实执动作 | 终止 | 官方分数 |
|---|---:|---:|---:|---|---:|
{table}

完整wire、接受历史前缀、实际first-forward IDs/pixels/grid、有效生成设置、输出IDs/EOS与回复、request/reply seals及事件链逐一绑定。Flash另经CPU重载{flash['verified_complete_Flash_replies']}份完整实际forward tensor、重建原始二元head与概率，0额外推理/GPU分配。服务实际UID1033、完整命令/start/UUID、主17锁/Flash9锁及全部compute已核，GUI实际UID1015；不依赖running字段。主state1184份、54,713,457,120字节，BF16/SDPA，模型无CPU/disk offload。成本须计8卡实际保留时间、每卡峰值与延迟，不把累计生成秒数当墙钟/货币/能耗。

## 判定边界与效果

Flash固定revision `9ff7cf9838e59df461c276b7699d56b244d2af58`，每次只有完整单图和同一个通用可观察性问题，无任务、主上下文、候选、前图、累积KV。YES将同一PNG交主模型，不追加解释或概率；NO等待0.5秒，从同一环境持续新复拍至YES或手停。技术失败保全后停，不能当NO。主模型完整接受历史、原图、BF16/SDPA、2048输出、50决策/70actor、原seed及原生提示/解析/执行/评分保持；无旧上下文语义judge、私有评分答案不入模型、网站不重置。

单图门控不能保证识别清晰旧帧，也不证明动作正确。Mirage语义审查尚未完成，降幅null，尚未证明防御有效。后续按原图和合法历史逐候选审查，并分开报告首次错误、放行/实执错误、误拦/复拍等待、官方完成和技术故障；发生后纠正仍计数，纯nativeWAIT排除，未知保持未知。不得靠挑选阳性、一直等待、少动作或官方分数宣称效果。

目标保持active，不恢复任何旧attention/UI-TARS/VWA20/32或28队列。手停可创建 `{R4090}/STOP`；在途调用返回后停止后续转交和动作。
'''
name='Flash七卡显存修复与完整GUI进展-20261114.md';(pub/name).write_text(report,encoding='utf8')
save(pub/'publication-seal.json',{p.name:sha(p)for p in pub.iterdir()if p.is_file()})
pointer={'publication':str(pub),'status':str(pub/'status.json'),'status_sha256':sha(pub/'status.json'),'report':str(pub/name),'report_sha256':sha(pub/name),'publication_seal_sha256':sha(pub/'publication-seal.json'),'manifest_sha256':ready['manifest_sha256'],'time':ts/1e9,'goal':'active','Mirage_reduction':None}
temporary=HERE/('.pointer-'+str(ts)+'.json');save(temporary,pointer);temporary.replace(HERE/'experiment-current.json')
head=f'''## 最新：2026-11-14 七卡主27B＋独立Flash显存准入通过，29未开始GUI已续跑

最新权威 `flash-ample-memory-gui-20261114-linked06/experiment-current.json` → `{pub.name}/status.json` 与 `{name}`，覆盖旧“仍未续跑/仅三卡”快照。用户明确充裕显存继续至效果；实际3090主0–6/Flash7、BF16/SDPA/全部原图和接受历史保留。原2正常＋1OOM终局不重跑，新29中七任务14完整对，T000旧帧门控为无完整新对照诊断。

linked06使用1184张量source-bound CPU显式映射，视觉+embedding0、64层在1–6、norm/lm_head6。chunk保持head/矩阵乘/规约/元素操作数顺序和精度，三个私有dead点乘缓冲复用；逐项恢复原表达式、去掉del后AST才相同，不称原AST未改。MLP死SiLU缓冲复用及长输入allocator闲置块释放，实际各卡原权重输出字节相同、输入未改。9个chunk输出状态＋真实15图连续3步全词表logits/IDs逐位一致，每遍192MLP/48chunk；新50图53167tokens完整126输出IDs等于linked02，最小reserved峰值余量{ready['minimum_reserved_peak_headroom_GiB']:.2f}GiB。双臂同版，无CPU/disk模型offload，不保证所有未来历史最坏容量。原七卡/linked05 OOM、linked02/04余量不足、linked03head分组逐位失败均保全，0正式GUI，不再运行这些旧入口。当前69文件manifest `{ready['manifest_sha256']}`，不可热改/重复提交。

截至{stamp}，新非基础设施终局{len(good)}/29，技术终局{len(terms)-len(good)}；核验快照{live['verified_main_replies']}主回复/{live['verified_Flash_replies']}Flash/{live['environment_action_events']}实执事件及SHA链，实际UID/fullcmd/start/UUID/主17锁/Flash9锁已核。Flash仍单完整图固定通用问题、空上下文，YES原PNG转交，NO按用户选择持续同环境复拍直到YES或手停；技术故障不是NO。单图不能证明旧帧新鲜或动作正确。0新条件语义改变/付费API，私有答案不入模型，网站不重置。

语义审查未完成、Mirage降幅null、未证明防御有效；目标active，后续审首次/接受/实执错误、误拦与官方完成。原图/完整历史/原预算保留，任何技术终局完整保存后停，不重刷终局。所有旧队列不恢复，以下旧头只保留历史。

'''
for n in prior:
 assert(BASE/n).read_bytes()==prior[n]
 (BASE/n).write_bytes(head.encode('utf8')+prior[n])
payload=io.BytesIO();names=['status.json',name,'experiment-README.md','capacity-audit.json','live-audit.json','terminal-audit.json','Flash-CPU-audit.json']
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
out={'root':str(r),'verified_files':len(EXPECTED),'runtime_sources_changed':False,'new_model_GUI_calls':0}
with(r/'delivery-receipt.json').open('x')as f:json.dump(out,f,indent=2)
print(json.dumps(out))
'''
 raw,op=remote(host,code,'deliver-verified-GUI-progress-'+host,private_prefix='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n');deliveries.append({'host':host,'result':json.loads(raw),'operation':str(op)})
save(HERE/('publication-created-'+str(ts)+'.json'),{'pointer':pointer,'deliveries':deliveries})
print(json.dumps({'report':str(pub/name),'current':str(HERE/'experiment-current.json'),'complete':len(good),'expected':29,'Mirage_reduction':None},ensure_ascii=False))
