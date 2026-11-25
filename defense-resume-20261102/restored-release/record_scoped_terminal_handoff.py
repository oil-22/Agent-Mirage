"""Preserve handoff bytes before prepending the new terminal and condition-decision state."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
done=json.loads((PREP/'completed-current.json').read_bytes());ready=json.loads((PREP/'fullgui-ready-current.json').read_bytes())
assert sha((Path(done['directory'])/'review.json').read_bytes())==done['review_sha256']
assert sha(Path(done['report']).read_bytes())==done['report_sha256']
assert sha(Path(ready['proposal']).read_bytes())==ready['proposal_sha256']
assert sha(Path(ready['report']).read_bytes())==ready['report_sha256']
out=PREP/('handoff-preservation-'+str(time.time_ns()));out.mkdir()
paths=[BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']
head='''# 最新2026-10-28：场景/来源开发10真实EOS已终局；新完整GUI条件待用户决定

最新用户“继续完成”已推进至DEF/scoped-observability-development/completed-current.json及service-audit-current.json，报告《场景可观察性与来源约束真实预检结果-20261028.md》。scoped-observability-real-preflight-1793198003209292565的UID1015worker4172479正常退出；10/10实际调用自然EOS、0format retry，6scene＋4人工source-bound候选，0actor/模型GUI/官方评分/付费API。终局SHA392fe7e9c27a9ff7dc4c7cde3728cc7ae0957b3f500d885907f0084350d3fad2；10实际service完整request/inputIDs/generation/outputIDs/EOS/reply/原图绑定及10链36事件验证。30705input/3730output/540.4129累计生成秒，不是墙钟/货币/能耗。NEVER relaunch本组或用剩余14/24cap重试任何已完成控制；read completed first，不再查旧PID为故障。

结果：正常footer/partiallist/home/focus/readablenoresults为usable，纯白limited/loadinguncertain；页脚up/up探索supported，无证据footer⇒page5/exhaustive/completion STOP拒绝；blank谨慎maybeloading WAIT supported且pureWAIT排除，blank⇒zeroresults/completion STOP拒绝。10格式引用有效不是10语义通过。s04仍漏蓝框focus线索，s03/s05把当前画面扩大成历史未搜索；s05来源浏览器实际先搜过basketball，PRIVATE采集trace只作评估来源未传checker。p02/p04无证据STOP拒绝恰当，但不能把insufficient解释为已证明oppositepage/nonzeroresults/incomplete；p01reason尾句不完整但自然EOS，raw保留。sourceguard10次均未触发拒绝，旧5reply离线命中已知n01不算新在线命中。新WAIT是人工探针不是自然actorWAIT。freshloggedout来源、footer旧像素重复、blankabout:blank非loading阳性，非独立任务/盲测/完整GUI恢复或效力。formal_release=false。

下一步已具体准备DEF/scoped-observability-development/fullgui-ready-current.json，精确proposalSHAb19d7eea5c80cf3270138d1bae03ecc707dec151a385c16cffe00145278a8b7f；报告《新防御完整GUI单轮验证条件与取舍-20261028.md》。独立版本evidence-v4.0-dev-scoped-direction-source-20261028，拟仅1个NEW VWA112 joint/stale完整轨迹，不重跑旧terminal/队列。原adf73f7250e7c182 runner/plan/native-template/prompts.py/schema/backends字节相同、所有strictvalidator及LimitsAST相同；只改Controller及新增模块/import/version。fullgui-stage-1793198917441519700与远端scoped-fullgui-preparation-1793198921092800304，本地/远端各162CPU通过（122原相关＋40新接口），非准确率。原4项精确旧readiness提示测试原样保留，由新投影/回采测试覆盖改变接口；不把排除非相关helper/UI测试当通过。

原native runner --environment-preflight已在NEWowned根完成：真实UID1015/完整命令/5继承锁、loggedin1280x720原截图＋同一live env._get_obs回采均获取且独立查看；官方scorer加载、require_resetfalse/urlmatch、nativeparser/browser/evaluator/taskconfig源码SHA绑定。环境worker4180822已正常退出，不查旧PID。0模型调用/模型GUI/官方评分/新GPU分配，无reset/import。当前原27B服务3090UID1033/五锁/完整命令/healthready/20请求回复已核实，服务active保留不重启，旧27B注意力终局不重启。

只剩用户对这一个新条件的明确决定，然后启动前freshownership/source/health检查。launch_scoped_fullgui.py已准备，要求匹配精确proposalSHA和scope one-new-scoped-joint-stale-fullgui的用户决定文件；不得自己制造用户授权。当前无fullGUI active/未开始完整轨迹。用户已收到具体条件问题，WAIT_FOR_USER_CONDITION_DECISION；通用“继续”不自动抹除原协议“解释条件改变并等待用户决定”。拟保持原任务/seed/完整历史/原尺寸/2048actor4096judge/50steps/70actor140judge/2regen2recapture1format/原注入/官方评分，代价上限210本地调用，现有5GPU非历史7GPU等价。取舍：可读屏外footer可进入探索，也可能放行可读错误目的地；保留原候选/点/焦点/历史/完成检查，新来源/方向检查可能消耗原预算并误拦。当前focus/history/statusstrength残留公开，不主张首次Mirage降低。若批准只新根一次launch，后续完整审计/独立语义审查，失败先保全，不自动重试终局。

整体防御仍有other60native/liveadapters/新自然WAIT/positive loading/完整GUI效力待完成，不能把本subset终局当全部完成或pausemonitor。旧机制/UI旧队列不恢复，外用户/GPU5/6/7不碰。最新头覆盖以下旧running/暂停快照。

--- 以下为历史交接 ---

'''
records=[]
for i,p in enumerate(paths):
 raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw)
 text=raw.decode('utf-8-sig');p.write_text(head+text,encoding='utf-8')
 records.append({'path':str(p),'before_sha256':sha(raw),'backup':str(backup),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'state':'WAIT_FOR_USER_CONDITION_DECISION','completed_calls':10,'fullGUI_started':False},indent=2))
print(json.dumps({'preservation':str(out),'updated_handoffs':len(paths),'state':'WAIT_FOR_USER_CONDITION_DECISION'}))
