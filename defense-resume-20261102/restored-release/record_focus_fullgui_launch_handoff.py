"""Record direct launch authorization and actual once-only worker without changing old decisions."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
head=f'''# 最新2026-10-29：用户“启动实验”已授权并启动修复版单轮完整GUI

本头覆盖下方旧“完整GUI未授权/不可启动”的当前状态；旧repair-first决定原样保留。最新直接人类指令“启动实验”已绑定focus-history-fullgui-development/user-launch-decision.json，精确新proposal7778718de26875965b6da41c0cb9dc2cf26d80391205e05f3f1299b9fb0a4d57。仅1轮原VWA classifieds112/joint/stale_replace，使用已实测修复版本evidence-v4.0.2-dev-current-only-scope-20261028，不是旧未修复proposal。

权威focus-history-fullgui-development/fullgui-launch-current.json、inspection-current.json、fullgui-ready-current.json。新root {launch['root']}；UID1015/PID{launch['pid']}仅作定位，必须核实实际fullcmd和5个继承tasklocks及batch.lock，不能只信status/PID。原3090UID1033服务fullcmd/5GPUlocks/service.lock核实，已有实际新service request；推理中health延后不当服务故障。inspect_focus_history_fullgui.py只读事件SHA链前缀/真实进程锁/日志，inspect_resumed_defense_service.py核实服务与actualrequest/replies。NEVER再次launch；远端focus-history-fullgui-active-20261029.json为一次性persistentreceipt，即使进程退出也先审计而非重启。

原任务/seed/完整历史/1280x720/BF16/SDPA/2048actor4096judge/50steps/70actor140judge/2regen2recapture1format/原注入时点/官方URLmatch评分保持；原strictvalidators/Limits/runner/native模板/plan/prompts/schema/backend逐SHA/AST同旧完整GUI准备，只有隔离Controller和辅助提示/来源/方向模块条件改变。新增current-only历史执行断言和过去事件来源资格约束不改verdict/action，不补相反事实；可能误拦当前屏幕日志/历史UI、耗原预算、正则漏改述，eligible/unflagged不等于语义批准。6focus对照正确不保证readiness/目标typing联动或GUI恢复，主历史guard此前0在线拒绝。仅单个已知任务开发，不是正式效力/首次Mirage降低证明。

本地/远端各196CPU检查通过；新原native登录环境0调用预检和same-live env._get_obs回采实际完成，两原图已独立查看My account/Logout。父记录器遍历/proc fdinfo/8时遇子进程关闭句柄而FileNotFoundError，原代码/子日志/终局保留；只恢复收集已正常完成预检回执，0重跑/0模型调用。新launcher已跳过瞬时关闭fd并逐目标锁确认，不放宽实际锁。环境源/站点Id/owner/端口/原生scorer源码启动时再核实，未reset/import，无新GPU分配/付费API。

终局后必须先封存全部日志/原图/事件/输入/回复/失败/SHA，再collect actualservice fullrequest/inputIDs/generation/outputIDs/EOS/imagebindings，核实原预算/注入/官方分数，独立图像/法律历史/候选语义审查；初始/接受/执行错误/恢复分开，纯nativeWAIT排除，发生后恢复不抵消。技术失败不是模型零；新终局不自动重试或扩预算。待完成其他60native/liveadapters/自然WAIT/loading阳性/完整防御效力，monitorACTIVE；旧机制/UI队列/旧终局与27B注意力终局绝不重启，外资源/GPU5/6/7不动。健康运行保持安静，只报有意义结果/失败修复/需要用户决定。

--- 以下为历史交接 ---

'''
out=PREP/('handoff-preservation-'+str(time.time_ns()));out.mkdir();records=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
 raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');records.append({'path':str(p),'before_sha256':sha(raw),'backup':str(backup),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'authorized':True,'launched':True,'monitor':'ACTIVE'}
(PREP/'handoff-current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
