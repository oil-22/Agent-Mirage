"""Preserve handoff bytes and prepend the completed, repair-first authority."""
import hashlib
import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
PREP = BASE / 'focus-history-repair-development'
sha = lambda b: hashlib.sha256(b).hexdigest()
done = json.loads((PREP / 'repair-combined-current.json').read_bytes())
head = f'''# 最新2026-10-28：焦点/历史修复两轮已终局17EOS；完整GUI仍未授权

用户明确选择“先修复焦点和历史推断问题”，上一proposal b19d7eea5c80cf3270138d1bae03ecc707dec151a385c16cffe00145278a8b7f未授权，fullgui-decision-current.json及focus-history-repair-development/user-decision.json为approved=false。旧ready/proposal只是准备记录，不运行launch_scoped_fullgui.py，不自动重问旧问题。先read focus-history-repair-development/repair-combined-current.json、completed-current.json及readiness-supplement/completed-current.json，报告《焦点与历史推断修复真实预检结果-20261028.md》。本头覆盖下方旧running状态。

两独立条件：v4.0.1-dev-focus-history-scope第一轮12逻辑控制/12EOS/0retry；v4.0.2-dev-current-only-scope补充4逻辑控制/5EOS/1原formatretry。合计17实际service完整request/inputIDs/generation/outputIDs/EOS/reply/image绑定，16链73事件，两个UID1015worker实际均退出。严禁重启launch_focus_history_repair.py、launch_focus_readiness_supplement.py或用余7/24cap重试已完成控制。各root只能称各自12/5calls，不把parentroot写17calls。第一轮终局SHA2a278eb34d329eb63057a77abffcb2fbe9d04e2d5a95c08ab9f7273e7e3042a0；补充0e18798e331dee0070ac387bf60d432fd56bd79c857675bd1a6f534e846bff72。

焦点专用f01..f06三蓝框/普通框配对均匹配可见线索，Keyword/Your search/City分开；Cityfocus不等于Keyword目标typing许可，也不证明先前点击因果。首轮s01/h02/h03历史失败保留：当前输入已有basketball不证明搜索执行，当前铜制页不反证所有早先检视，plan-only不等于完成；正确拒绝STOP不代表解释正确，部分reason自然EOS仍尾句未完。h04人工plan-only WAIT按用户口径排除，非自然actorWAIT。

新增current_only_history_scope.py在隔离Controller调用原strictvalidator后暂扣窄范围确定执行历史断言，原1formatretry/raw不改、不注入相反事实/正确页/动作。b01首次自然生成search has not been submitted，真实拒绝，原重试后No confirmation；首错不抹去。最终b01readiness仍未明确描述Keyword蓝框，不能拿专用focus成功替代。b02确见Cityfocus，may still be settling只是有资格的假设非loading阳性。b03无早先图时当前fact supported/历史never-search insufficient；b04真实earlier篮球图反驳无先前结果并正确引用reference1。主historical_event_source guard在线0拒绝，不能把b03改进归因它；旧s01/h02/h03离线工程replay不算新在线命中。sourcepolicy借formatretry通道不等于JSON畸形。较早assistant只证明报告/计划，非执行；保守来源策略可能误拦当前画面日志/历史UI，正则窄且可漏，未命中不是semantic批准。

全部16逻辑控制仅6唯一1280x720图，logged-out脚本采集、人工候选/plan上下文、同站点非盲选择，非16任务/semanticpasses/全GUI效力。prior-results/query-ordinary同PNG；另一查询实际350铜制商品不是noresults。PRIVATE期待不传checker。0actor/模型GUI/官方评分/付费API；原输入/历史/BF16/SDPA/4096输出/1retry不缩不扩。原strictvalidators/Limits及native模板/runner/backend原样，既有candidate-blind投影未变；167工程CPU及补充34本地远端、补充原122相关CPU保留，不作准确率。

累计{done['input_tokens']}input/{done['output_tokens']}output tokens/{done['summed_generation_seconds']:.4f} summedgenerationseconds，非墙钟/货币/能耗，不含加载/采集/分析。3090UID1033五卡GPU0–4原27B服务已fresh核实fullcmd/5GPUlocks/service.lock/healthready；与历史7GPU不假定逐位/成本等价。外用户/GPU5/6/7不碰。新焦点目标typing联动、历史计划与执行冲突、自然actorWAIT/loading阳性及完整GUI效力仍需准备/验证，formal_release=false。不要自动启动旧完整GUI条件、旧机制/UI队列或27B注意力终局。other60native/live adapters仍未完成，monitorACTIVE。

--- 以下为历史交接 ---

'''
out = PREP / ('final-handoff-preservation-' + str(time.time_ns()))
out.mkdir()
records = []
for i, path in enumerate([BASE / 'README.md', BASE / 'REPAIR_HANDOFF.md', BASE.parent / 'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw = path.read_bytes()
    backup = out / (str(i) + '-' + path.name)
    backup.write_bytes(raw)
    path.write_text(head + raw.decode('utf-8-sig'), encoding='utf-8')
    records.append({'path': str(path), 'before_sha256': sha(raw), 'backup': str(backup), 'after_sha256': sha(path.read_bytes())})
(out / 'receipt.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
pointer = {'directory': str(out), 'receipt_sha256': sha((out / 'receipt.json').read_bytes()), 'repair_terminal': True, 'fullGUI_authorized': False, 'monitor': 'ACTIVE'}
(PREP / 'handoff-current.json').write_text(json.dumps(pointer, indent=2), encoding='utf-8')
print(json.dumps(pointer))
