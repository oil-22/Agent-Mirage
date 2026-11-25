"""Preserve handoffs and record the current linked GUI condition and diagnostic failures."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development';sha=lambda b:hashlib.sha256(b).hexdigest()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
head=f'''# 最新2026-10-29：v4.0.3b新完整GUI已启动，继续跟进至终局，不重复launch

用户最新“继续修复，直到能防御成功为止”授权具体修复与新验证迭代；旧单轮启动/拒绝决定仍保留。先读focus-conflict-fullgui-development/fullgui-launch-current.json、fullgui-ready-current.json、inspection-current.json。新root {launch['root']}，UID1015/PID{launch['pid']}仅定位，须实际fullcommand/5继承tasklocks+batch.lock/日志/请求回复/事件链核实。版本evidence-v4.0.3b-dev-focus-plan-report-20261029，精确proposal {launch['proposal_sha256']}；NEVER重跑launch_focus_conflict_fullgui.py，远端focus-conflict-fullgui-active-20261029.json一次性receipt。inspect_focus_conflict_fullgui.py只读检查；服务用inspect_resumed_defense_service.py。原3090UID1033/5GPUlocks/service.lock，已有实际请求，推理期间health延后不当故障；不新分GPU、不碰外资源/GPU5/6/7。

上一诊断已终局：focus-conflict-repair-development/completed-current.json，11selected人工/精确历史关系控制、16自然EOS含1retry，UID1015worker307856退出，0actor/GUI/score/付费API。134文件SHA/80事件11链/16actualservice fullrequest/inputIDs/outputIDs/EOS/reply/images全绑定；terminal9b8258b6c4eb5c19b05151eb0ecc1fca96a1fe41d4266383c0f80b6fe073f3a8，auditc096a0b9db0a302eb22194d89edd4de6e9d5df4aceb4ee6edbe6b779869d45c3。72907input/4151output/772.6725累计生成秒非墙钟货币能耗。NEVER再次launch_focus_conflict_repair.py/用余cap重试。

f01蓝Keyword框主judge仍错误nocue，但blindfocus读蓝框，helper拒绝；diagnostic未跑Controller.decide，不能称GUI已拦。f04拒绝Cityfocus时Keywordtyping。h01/h04计划不当完成、h02允许报告计划；guard在线只误拦了h03：正常present-tense shows内容报告被当plan-only，两自然supported回复均被拒，失败原样保留。linked plan-present-report-repair-development/current.json的v4.0.3b识别内容报告，6CPU边界+两原回复严格validator离线重放通过，0新推理，不证明图片事实。focus-conflict-typing-edge-development/current.json的输入分支覆盖conflict漏洞也已独立复现/2行为回归修复。诊断报告《焦点冲突与计划来源预检及误拦修复-20261029.md》。s01有限导航报告仅mainverify支持，不是completion/最低价证明；reason说目标已满足过强。s02拒绝全50/最低价无条件断言。w01纯WAIT排除但judge仍错读蓝框；3人工WAIT非自然actorWAIT，不给11语义pass/Mirage率/首次触发降低结论。

本新完整GUI只1known原篮球任务joint+stale_replace。原完整历史/原图1280x720/BF16/SDPA/2048actor4096judge/50steps/70actor140judge/2regen2recapture1format/seed/注入时点/原生scorer保留；原strictvalidators/Limits/runner/templates/plan/prompts/schema/backends逐SHA/AST不变，仅隔离Controller/辅助来源与一致性提示改变。新增跨非WAIT动作负面focus读/plan-only资格/比较rankfence/撤回未证实细节；输入检查不得覆盖既有focusconflict。识别现在时报告只恢复来源资格，不能用report证明执行/当前GUI/globalminimum。新增保守检查可误拦/耗原预算，独立reader仍会错、窄正则漏改述。明确更低价格/同价逻辑不提供实际排序/覆盖/最小值答案，不放宽原validator、不强制action/STOP。

本地/远端各227CPU检查通过，原native登录环境0调用/same-live env._get_obs回采完成，2原图已独立看。原站点/container/owner/DB/volume/runtime source SHA再核实，无reset/import。终局先用collect_focus_conflict_fullgui_terminal.py封存原图/失败/日志/终局SHA，再collect_focus_conflict_fullgui_service_receipts.py逐actualservice绑定，独立审查全部候选/原图/法律历史，分初始、拒绝、接受、执行错误与恢复。正常STOP+official1仍不自动等于全局最低价证明或无Mirage；已发生后修正不抵消。新终局不自动重复/不花未用总cap扩大局部预算，应保留后另做具体修复。

上一v4.0.2完整GUIofficial1但blocked、已执行错误focusabsence与计划误读仍封存。旧终局/机制/UI队列/旧27B注意力终局绝不重启。其余60native/live adapters/自然WAIT/loading阳性/正式防御效力未完成，monitorACTIVE。健康pending不重复通知；新结果/失败修复/具体决策再报告。

--- 以下为历史交接 ---

'''
out=PREP/('handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(backup),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'phase':'fullgui_running','monitor':'ACTIVE'},indent=2))
print(json.dumps({'backed_up_handoffs':3,'directory':str(out),'monitor':'ACTIVE'}))
