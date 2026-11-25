"""Publish verified stopped state; no experiment mutation or retry."""
import base64,hashlib,io,json,time,zipfile
from datetime import datetime,timezone,timedelta
from control import HERE,BASE,R3090,R4090,remote,save,sha

evidence=max((p for p in HERE.glob('postexit-evidence-*')if(p/'summary.json').exists()),key=lambda p:p.stat().st_mtime_ns)
for n,h in json.loads((evidence/'seal.json').read_bytes()).items():assert sha(evidence/n)==h
s=json.loads((evidence/'summary.json').read_bytes());m=json.loads((evidence/'3090.json').read_bytes());g=json.loads((evidence/'4090.json').read_bytes())
assert s['phase']=='stopped_on_technical_failure'and s['normal_terminals']==2 and s['technical_terminals']==1 and s['unstarted']==29
failed=s['failed_requests'][0]
zone=timezone(timedelta(hours=8))
fmt=lambda t:datetime.fromtimestamp(t,zone).strftime('%Y-%m-%d %H:%M:%S +08:00')
checked=fmt(s['read_time']);stopped=fmt(m['primary_terminal']['time']);failure_time=fmt(failed['failure']['time'])
ts=time.time_ns();pub=HERE/('postexit-progress-publication-'+str(ts));pub.mkdir()
for name in ['HANDOFF.md','README.md']:(pub/('prior-parent-'+name)).write_bytes((BASE/name).read_bytes())
(pub/'prior-experiment-current.json').write_bytes((HERE/'experiment-current.json').read_bytes())
(pub/'evidence-summary.json').write_bytes((evidence/'summary.json').read_bytes())
status={'phase':'stopped_on_technical_failure','read_time_local':checked,'primary_stop_time_local':stopped,'expected_trajectories':32,'normal_terminals':2,'technical_terminals':1,'unstarted':29,'evidence':str(evidence),'evidence_seal_sha256':sha(evidence/'seal.json'),'counts':{k:s[k]for k in ['actor_attempts','complete_actor_replies','actor_technical_failures','Flash_replies','Flash_YES','Flash_NO','environment_actions','full_model_postexit_files_verified','full_GUI_postexit_files_verified']},'normal_results':s['normal_results'],'failed_request':{'run_id':failed['run_id'],'decision':failed['decision'],'input_tokens':failed['input_tokens'],'history_messages':failed['history_messages'],'image_count':failed['image_count'],'actual_forward_calls':failed['forward_count']['actual_forward_calls'],'directory':failed['directory'],'wire_sha256':failed['wire_sha256'],'seal_sha256':failed['seal_sha256'],'failure_time_local':failure_time,'type':'CUDA out of memory during original primary prefill; no generated reply'},'actual_all_experiment_model_and_GUI_processes_exited':True,'GUI_running_snapshot_stale':True,'failure_and_all_original_inputs_preserved':True,'new_model_GUI_calls_by_inspection':0,'queue_restarted':False,'conditions_changed':False,'semantic_review_completed':False,'Mirage_reduction':None,'defense_effectiveness_proven':False,'created':ts/1e9}
save(pub/'status.json',status)
name='Flash完整GUI实验进展与OOM中断-20261114.md'
report=f'''# Flash完整GUI实验进展：已中断，防御效果尚未证明

截至北京时间 **{checked}**，这批32条完整GUI实际状态为 **2条完成、1条技术失败、29条未开始**。主27B于 **{stopped}** 停止；主模型、Flash、launcher和GUI runner均已按实际UID/完整命令/start ticks确认退出。此前启动报告和GUI `running` 快照是历史状态，不能继续当成正在运行。

| 部分 | 结果 |
|---|---|
| T000正常、无门控 | 8次主回复、7次实际环境动作，model_stop，官方0 |
| T000正常、Flash门控 | 8次主回复、8次Flash YES、7次实际环境动作，model_stop，官方0，0复拍 |
| T000旧帧、无门控 | 第15步主模型prefill OOM；此前14次完整回复/14次实际动作；技术终局、官方评分null |
| 其他29条 | 未开始，包含尚未运行的旧帧Flash门控轨迹 |

## 中断原因

失败请求 `primary/requests/00031` 包含完整30条消息、15张原始历史图、15,367输入tokens。主27B在三张3090（物理4–6）的原BF16/SDPA运行条件下，于prefill的原生线性注意力运算触发OOM，实际forward计数1，没有完整生成回复。错误记录为逻辑GPU1需再分配362MiB、当时空闲332.69MiB；其当时PyTorch已分配21.83GiB、另保留未分配1.22GiB。错误位置和显存记录证明显存不足，单凭保留空间不能断言仅靠allocator设置就可修复。

主服务返回503后退出，GUI清理的`/end`又遇到连接拒绝，因此最后的GUI `running` 文件没更新。失败轨迹terminal已经写入，完整batch postexit seal覆盖该terminal、截图、动作、轨迹与日志；其没有单独attempt seal不能被隐瞒为全轨正常完成。此次失败发生在无Flash对照臂，不是Flash把图像判成NO或门控阻止了错误。

## 已核验的实际证据

本批共31次主模型请求：30份自然EOS完整回复+1次prefill OOM，另有8份Flash实际回复；真实环境动作总计28。8次Flash均YES，实际GUI还未自然触发NO及持续复拍路径。旧的fixture NO控制不混入这8次实测。

本次只读取证，逐文件SHA核验 **{s['full_model_postexit_files_verified']}个模型侧postexit文件、{s['full_GUI_postexit_files_verified']}个GUI batch文件**，另核控制侧postexit seal、所有31请求seal、完整首forward输入、8个Flash回复、原54冻结来源文件和全部主/Flash/Controller事件链。未重新加载权重、推理、截图、评分或重跑任何终局。原holder身份和九持有锁仍按实际证据记录；未操作外人进程或分配GPU。

证据：`{evidence}`。失败原请求、原图、完整历史、输入张量、错误和日志仍在原远端目录，seal已重新验证；所有旧终局保持不变。

## 当前可得结论及下一步

首个正常配对两臂官方分数都为0，不能视为防御改善。仅8次全YES且没有旧帧门控完整结果，也未完成候选Mirage独立语义审查，**目前没有降低Mirage触发率的证据**。官方分数、基础设施失败、门控判定与Mirage标签必须分别统计。

下一步必须先处理主27B保留完整图像/历史时的显存容量，并做独立容量验证，再以新关联attempt推进未开始部分。不能直接重新执行已经封存的失败或完成轨迹，也不能悄悄截断历史、缩图、降低精度、增加输出预算或把技术失败当作模型零分。本次没有重启队列或改变条件。
'''
(pub/name).write_text(report,encoding='utf8')
save(pub/'publication-seal.json',{str(p.relative_to(pub)):sha(p)for p in pub.iterdir()if p.is_file()})
pointer={'publication':str(pub),'status':str(pub/'status.json'),'status_sha256':sha(pub/'status.json'),'report':str(pub/name),'report_sha256':sha(pub/name),'publication_seal_sha256':sha(pub/'publication-seal.json'),'phase_at_evidence_time':'stopped_on_technical_failure','completed_at_evidence_time':2,'technical_terminals':1,'unstarted':29,'expected':32,'Mirage_reduction':None,'created':ts/1e9}
head=f'''## 最新：2026-11-14 实查Flash完整GUI已于11月13日OOM退出；2完成+1技术终局+29未开始

最新权威 `flash-gated-full-gui-20261113/experiment-current.json` → `{pub.name}/status.json` 与 `Flash完整GUI实验进展与OOM中断-20261114.md`；实际只读取证 `{evidence.name}`。主服务于北京时间{stopped}停止，主27B/Flash/group launcher/GUI outer和runner均按实际UID/full command/start退出；旧running/启动中头过期。不要重跑stage/service/gui或旧终局。

本32新轨迹当前2正常终局、1OOM技术终局、29未开始。T000 clean两臂各8主回复/7实执、model_stop、官方0；门控8Flash全YES、0NO/复拍。T000 stale_replace baseline第15步、30消息/15原图/15367输入token，原BF16/SDPA三卡主27B在prefill OOM，0本次生成回复；此前14回复/14实执。技术终局官方null，不是模型语义零分。主退出后GUI /end连接拒绝导致旧running快照保留；失败terminal由完整batch postexit seal覆盖，缺单独attempt seal已明确。旧帧Flash轨迹未开始。

31主请求=30自然EOS+1OOM，另8Flash，28真实环境动作；模型839 postexit文件、GUI115 batch文件及control seal、31请求seal/首forward原tensor、8Flash和全部链/54冻结源SHA逐一核对。失败请求00031完整wire/历史/原图/ID/pixels/grid/原始错误/日志全保留。实际holder身份和九锁记录仍核实；本次0新模型/GUI/评分/资源分配，无条件变更/自动重试。Mirage语义审查未完成、降幅null、未证明防御有效。

下一必需步骤是完整历史的主模型显存容量修复与独立验证，再以新关联attempt推进未开始部分；不截断/缩图/改精度/扩预算，不重刷终局。用户原持续复拍选择保持，无需复问；技术OOM不当成NO。所有旧attention/UI-TARS/VWA20/旧32/28终局不恢复。以下旧头只保留历史。

'''
for fn in ['HANDOFF.md','README.md']:
 old=(pub/('prior-parent-'+fn)).read_bytes();assert(BASE/fn).read_bytes()==old
 (BASE/fn).write_bytes(head.encode('utf8')+old)
assert(HERE/'experiment-current.json').read_bytes()==(pub/'prior-experiment-current.json').read_bytes()
tmp=HERE/('.postexit-current-'+str(ts)+'.tmp');save(tmp,pointer);tmp.replace(HERE/'experiment-current.json')
save(HERE/('postexit-publication-created-'+str(ts)+'.json'),pointer)
payload=io.BytesIO();files={}
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED)as z:
 for fn in ['status.json',name,'evidence-summary.json']:
  raw=(pub/fn).read_bytes();z.writestr(fn,raw);files[fn]=hashlib.sha256(raw).hexdigest()
 raw=(HERE/'experiment-current.json').read_bytes();z.writestr('experiment-current.json',raw);files['experiment-current.json']=hashlib.sha256(raw).hexdigest()
receipts=[]
for host,root in [('3090',R3090),('4090',R4090)]:
 code='ROOT='+repr(root)+'\nPUB='+repr(pub.name)+'\nFILES='+repr(files)+'\n'+r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
r=Path(ROOT)/'documentation'/PUB;r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():
  p=r/n;assert p.resolve().is_relative_to(r.resolve())
  with p.open('xb')as f:f.write(z.read(n))
assert all(hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in FILES.items())
v={'root':str(r),'verified_files':FILES,'runtime_sources_changed':False,'new_model_GUI_calls':0}
with(r/'delivery-receipt.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2)
print(json.dumps(v))
'''
 raw,operation=remote(host,code,'deliver-postexit-progress-'+host,private_prefix='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n')
 receipts.append({'host':host,'result':json.loads(raw),'operation':str(operation)})
save(HERE/('postexit-documentation-delivery-'+str(ts)+'.json'),receipts)
print(json.dumps({'report':str(pub/name),'current':str(HERE/'experiment-current.json'),'phase':'stopped_on_technical_failure','new_model_GUI_calls':0},ensure_ascii=False))
