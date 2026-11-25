"""Append current human repair-first steering with preserved old handoff bytes."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-repair-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
stage=json.loads((PREP/'current.json').read_bytes());launch=json.loads((PREP/'launch-current.json').read_bytes())
terminal=PREP/'completed-current.json'
if terminal.exists():
 done=json.loads(terminal.read_bytes());summary='修复诊断已终局：read focus-history-repair-development/completed-current.json、service-audit-current.json和报告；不可重跑已完成控制或用剩余cap重试。\n'+json.dumps(done,ensure_ascii=False)+'\n'
else:summary='新隔离修复诊断运行中，只运行inspect_focus_history_repair.py/read_focus_history_progress.py。实际UID/fullcmd/两锁/请求回复核实，不以旧PID或status自证。终局后collect_focus_history_receipts.py逐完整request/inputIDs/generation/outputIDs/EOS/图/回复绑定并独立审查；不得停在launch。\n'
head=f'''# 最新2026-10-28：用户明确选择先修焦点和历史推断，不授权上一完整GUI条件

用户对精确proposal b19d7eea5c80cf3270138d1bae03ecc707dec151a385c16cffe00145278a8b7f回复“先修复焦点和历史推断问题”。权威DEF/scoped-observability-development/fullgui-decision-current.json及DEF/focus-history-repair-development/user-decision.json，approved=false/REPAIR_FIRST_FULLGUI_NOT_AUTHORIZED。不要再把上一proposal当waiting approval/自动授权，不运行launch_scoped_fullgui.py；旧ready/proposal作为准备记录原样保留。没有fullGUI active，旧轨迹/其他队列/27B注意力终局不重启。

{summary}
权威DEF/focus-history-repair-development/current.json、launch-current.json、inspection-current.json。新根{launch['root']}；UID1015worker{launch['pid']}仅定位；实际focus-history-repair-development.lock及native-direction-development.lock。167CPU本地/远端通过，仅工程。12控制=6focus（Keyword/Your search/City各蓝框与普通框）＋2scene＋4source-bound历史/人工候选，原4096judge输出/1format retry，独立24callcap，0actor/模型GUI/官方评分/付费API。completed controls不得用剩余cap重试。

修复是prompt-only：分开当前可见focus cue与先前点击因果，当前空/查询不同不证明历史never-X，计划/报告不等于执行，insufficient不自动contradicted。独立focus仍只见当前原图/无历史/候选/目标，不强制usable；screen已有candidate-blind投影保持，actor/main完整历史不删。原strictvalidators/Limits/native模板不变，sourceguard扩到focus且仍用原1formatretry。版本evidence-v4.0.1-dev-focus-history-scope-20261028，不覆盖旧版本/结果。

新来源freshsource已封存source-current.json；6唯一1280x720原图均在调用前独立查看，中性observation alias后才传checker，PRIVATE期待未传。来源是loggedout脚本只读采集，不是原native actor轨迹。prior-results与query-ordinary同PNG，配对不是独立任务。计划采另一个查询，实际copper lantern＋数字返回1-12of350可读铜制商品，绝不是noresults；保留这次来源选择差异不改标签。h01实际先前篮球结果图公开给checker；h02没有earlierframe，不能推断neversearch；h03/h04是明确人工plan-only诊断上下文，不伪装原生历史。h04人工nativeWAIT排除，不当新自然actorWAIT/GUI恢复/正式效力。

此前scoped组10EOS终局和完整GUI0调用环境/162CPU准备原样保留，不重做。原服务3090UID1033/完整命令/实际五锁/healthready已核实，原27B/BF16/SDPA/GPU0–4五卡独立开发部署，外用户/GPU5/6/7不碰。焦点读对不自动证明目标field或typing正确；修复效果须看新真实回复及负例，不能只靠prompt或CPU宣布完成。整体other60native/真实WAIT/loading阳性/fullGUI效力仍未完成，保持monitorACTIVE，不自动恢复旧UI/机制队列。

--- 以下为历史交接 ---

'''
out=PREP/('handoff-preservation-'+str(time.time_ns()));out.mkdir();records=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
 raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');records.append({'path':str(p),'before_sha256':sha(raw),'backup':str(backup),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');(PREP/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'user_choice':'repair_first','fullGUI_authorized':False,'terminal':terminal.exists()},indent=2));print(json.dumps({'preservation':str(out),'terminal':terminal.exists()}))
