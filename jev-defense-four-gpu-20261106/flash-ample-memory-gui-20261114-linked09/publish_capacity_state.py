"""Durable current authority before formal GUI; no model or GUI calls."""
import json,time
from control import HERE,BASE,OUT,R3090,R4090,save,sha
ts=time.time_ns();pub=HERE/('capacity-publication-'+str(ts));pub.mkdir()
submission=json.loads((HERE/'service-submission.json').read_bytes());frozen=json.loads((HERE/'frozen-package.json').read_bytes())
value={'created':ts/1e9,'user_request':'按照充裕的显存预算跑起来，目标是跑出效果为止','goal':'active','latest_attempt':'flash-ample-memory-gui-20261114-linked09','capacity_state':'submitted; inspect actual process, proof and terminal files, never infer ready','formal_GUI_started':(HERE/'GUI-submission.json').exists(),'formal_trajectories_consumed':0,'old_terminals_reexecuted':False,'pending_GUI':29,'frozen_package':frozen,'service_submission':submission,'primary_output3090':OUT,'runtime_source3090':R3090,'GUI_root4090':R4090,'parent_prior_state_is_historical':True,'all_previous_memory_attempts_terminal_and_preserved':True,'source_review':'Explicit map from full1184 tensor layout; private dead output buffer reuse and allocator scheduling; strict numerical and3GiB per-card peak gates before GUI','semantic_conditions_changed':False,'Mirage_reduction':None,'new_model_GUI_calls_by_publication':0}
save(pub/'status.json',value)
head=f'''## 最新：2026-11-14 用户要求充裕显存继续；linked06八卡容量预检已提交，GUI尚待准入

最新容量准备权威 `flash-ample-memory-gui-20261114-linked09/{pub.name}/status.json`，源码manifest `{frozen['manifest_sha256']}`，69文件双机已核，service只提交一次。原holder九锁＋扩展八锁，3090主0–6/Flash7；必须读实际UID/fullcmd/start/锁/UUID/请求与terminal，不依running或本文submitted。新GUI29未开始，原2正常＋1OOM三终局不重跑；不能再次stage/service或恢复旧队列。

原七卡50图OOM；linked02完整EOS但峰值余量0.84GiB；linked03 head分组逐位失败拒绝/32文件封存；linked04完整50图126IDs相同但余量1.41GiB/94文件封存；linked05数值通过但自动映射尾卡11.68GB导致50图OOM/149文件封存。均已退出且不得重跑。当前linked06依据1184个实际权重张量显式分配完整连续decoder blocks，视觉+embedding0、层1–6、norm/lm_head6；三个chunk私有死缓冲点乘复用、MLP SiLU结果复用和长输入闲置allocator释放。数值AST仅在精确恢复原输出目的表达式和去掉del后相同，不声称原AST未改。须9核＋各卡实际MLP权重输出完整字节、真实15图连续3步全词表logits/IDs逐位、完整50图EOS全部126IDs等于linked02且各卡reserved峰值余量>=3GiB后，独立inspect_ready再放GUI。

完整原图/历史/BF16/SDPA/原生提示解析执行评分/2048输出/50决策70actor/seed不变，Flash仍单图独立固定通用问YES同PNG传主/NO0.5秒同环境持续复拍到YES或手停，无旧上下文语义judge。技术故障不是NO，完整证据保留后停；旧帧新鲜性不能靠单图保证。用户授权显存调度修复，无新语义条件决定，目标active，降幅null，未证明有效。以下旧头仅保留历史。

'''
head=head.replace('linked06','linked07').replace('69文件','70文件')
head=head.replace('以下旧头仅保留历史。','另：linked06因nonpersistent位置编码缓冲未纳入显式映射被严格CUDA检查拒绝，早于容量生成，26个postexit文件封存；本linked07加根默认及language rotary CUDA0，1187个真实parameters/buffers必须全部CUDA，不放宽检查。以下旧头仅保留历史。')
head=head.replace('linked07八卡','linked08八卡').replace('当前linked07','当前linked08').replace('70文件','71文件')
head=head.replace('本linked07加根默认及language rotary CUDA0，1187个真实parameters/buffers必须全部CUDA，不放宽检查。','linked07根默认导致加载时子模块被再次搬至GPU0而OOM，26文件封存；本linked08移除根钩子，只指定rotary CUDA0，静态nonpersistent缓冲按明确模块映射一次迁移且全字节/dtype一致，1187真实parameters/buffers必须全部CUDA，不放宽检查。')
for name in ['HANDOFF.md','README.md']:
 p=BASE/name;old=p.read_bytes();(pub/('prior-'+name)).write_bytes(old)
 assert p.read_bytes()==old;p.write_bytes(head.encode('utf8')+old)
save(pub/'seal.json',{p.name:sha(p)for p in pub.iterdir()if p.is_file()})
print(json.dumps({'authority':str(pub/'status.json'),'formal_GUI_started':value['formal_GUI_started'],'goal':'active'}))
