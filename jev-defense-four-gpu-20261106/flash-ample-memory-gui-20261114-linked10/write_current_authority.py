"""Publish the current submitted attempt without inferring any running/ready state."""
import json,time
from control import HERE,BASE,OUT,R3090,R4090,save,sha
ts=time.time_ns();pub=HERE/('capacity-authority-'+str(ts));pub.mkdir()
frozen=json.loads((HERE/'frozen-package.json').read_bytes());plan=json.loads((HERE/'package/plan.json').read_bytes())
value={'time':ts/1e9,'goal':'active','attempt':HERE.name,'submission':json.loads((HERE/'service-submission.json').read_bytes()),'frozen':frozen,'plan_version':plan['version'],'formal_GUI_started':False,'formal_GUI_trajectories_consumed':0,'remaining_GUI':29,'older_terminals_reexecuted':False,'status':'submitted; actual identities/locks/proofs/terminal must be read','main_gpu':list(range(7)),'Flash_gpu':7,'primary_synchronous_CUDA':'1','in_forward_allocator_purge':False,'runtime_root3090':R3090,'output3090':OUT,'GUI_root4090':R4090,'GUI_requires_independent_ready_audit':True,'Mirage_reduction':None}
value['placement']=plan['placement'];value['native_allocator_memory_fraction']=0.85;value['unused_cache_GC_threshold']=0.8
save(pub/'status.json',value)
head=f'''## 最新：2026-11-14 充裕显存授权继续；当前{HERE.name}已一次提交，GUI尚未开始

最新权威 `{HERE.name}/{pub.name}/status.json`、本目录README和实际输出文件。72文件manifest `{frozen['manifest_sha256']}` 双机逐文件核验；主3090物理0–6、Flash7，须实际UID/fullcmd/start/继承17与9锁/UUID/全部compute，不凭submitted/running/旧PID。目标active；只续29未开始GUI，原2正常+1OOM终局不可重跑，新七任务14完整配对与T000旧帧门控单列诊断。不得重复stage/service/gui。

当前明确完整权重映射：视觉+embedding0、64完整decoder blocks分到1–6、norm/lm_head6；没有根dispatch钩子，rotary明确CUDA0，静态nonpersistent缓冲仅按明确所属模块CUDA映射、全字节/dtype相同记录；真实1187参数/buffer仍严格全部CUDA。三个chunk私有死点乘结果缓冲和MLP死SiLU缓冲复用，原矩阵乘/规约/元素操作数顺序/精度保留；数值AST只能在精确恢复三个输出目的表达式并去del后相同，不能称原AST未改。主模型使用CUDA_LAUNCH_BLOCKING=1，移除forward内empty_cache；Flash调度不变。同步可能增加延迟，两正式臂一致，不能声称原非法访存根因或成本降低。

此前原七卡50图OOM；linked02完整EOS但最小余量0.84GiB；linked03 head分组逐位失败/32文件封存；linked04 IDs相同但余量1.41GiB/94文件；linked05自动尾卡11.68GB权重导致50图OOM/149文件；linked06漏nonpersistent buffer、严格CUDA拦下/26文件；linked07根钩子导致GPU0加载OOM/26文件；linked08严格设备/9chunk/12MLP及baseline三步通过，修复后遇CUDA非法访存/127文件。全部已退出、失败原始输入/tensor/代码/日志/postexit SHA保全，0正式GUI；不得重跑这些旧入口。当前源绑定这些不可变回执。

本次须9chunk完整输出状态、12实际权重MLP完整输出字节及输入未改、真实15图连续3步全词表logits/IDs逐位、新完整50图53167tokens自然EOS且全部126IDs等于linked02、每卡reserved峰值余量至少3GiB和inspect_ready独立只读核验后，再运行本目录control.py gui一次。3token工程cap不是EOS，50图为标明合成重复历史而非实跑50步；不保证所有未来历史最坏容量。任何新技术终局先完整保全，再另立attempt。

原完整图/接受历史/BF16/SDPA/原生提示解析执行评分/2048输出/50决策70actor/原seed保持；Flash仍固定revision、每次仅单完整图和通用问题、无任务/主历史/候选/前图/KV累积。YES同PNG转主不附文字概率，NO0.5秒同环境持续新复拍至YES或手停；技术失败不是NO，无旧上下文语义judge。网站不重置、私有答案不入模型、不抢外人。Mirage降幅null、未证明有效。以下旧头仅历史。

'''
head=head.replace('72文件','73文件').replace('64完整decoder blocks分到1–6','64完整decoder blocks分到0–6')
head=head.replace('以下旧头仅历史。','linked09已完整通过15图3步全logits与50图126IDs一致，但峰值reserved余量仅1.62GiB，157文件封存；本linked10将decoder blocks均分到所有七张主GPU（0层0–5，1层6–15，2层16–25，3层26–35，4层36–46，5层47–56，6层57–63），原生allocator比例0.85、闲置缓存GC0.8；可增加分配延迟/拒绝更大未来live集合，两正式臂同版，仍需每卡实测reserved余量>=3GiB后才放GUI，不缩图/截史/降精度/CPU offload。以下旧头仅历史。')
for name in ['HANDOFF.md','README.md']:
 p=BASE/name;old=p.read_bytes();(pub/('prior-'+name)).write_bytes(old);assert p.read_bytes()==old;p.write_bytes(head.encode('utf8')+old)
save(pub/'seal.json',{p.name:sha(p)for p in pub.iterdir()if p.is_file()})
print(json.dumps({'authority':str(pub/'status.json'),'goal':'active','formal_GUI_started':False}))
