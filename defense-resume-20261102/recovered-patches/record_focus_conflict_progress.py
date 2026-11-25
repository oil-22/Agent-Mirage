"""Back up all three handoff heads and record the active linked repair condition."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-repair-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
launch=json.loads((PREP/'launch-current.json').read_bytes());stage=json.loads((PREP/'current.json').read_bytes())
head=f'''# 最新2026-10-29：用户授权继续修复；v4.0.3源绑定诊断运行中，绝不重复launch

当前用户直接指令“继续修复，直到能防御成功为止”授权继续具体准备/修复/验证，旧“仅启动1轮”不覆盖本次新增迭代授权；旧决定、终局和seal保留。先读focus-conflict-repair-development/current.json、launch-current.json及inspection-current.json。root {launch['root']}，UID1015实际fullcommand及6继承tasklocks已核实；PID仅定位。NEVER重启launch_focus_conflict_repair.py，不复用已完成旧控制的剩余cap。本轮11个选择性人工候选/精确历史文本关系控制，最多24judge，原4096/1formatretry；0新actor/GUI/scorer，不是自然轨迹/独立效力样本。PRIVATE预期未上传，完整原图/法律prefix保留，source manifest {stage['source_manifest_sha256']}。

新增显式无focuscue断言跨动作盲读一致性、计划source资格、价格顺序比较fence、反馈撤回未证实细节。严格validator/Limits/native runner/2048actor4096judge/全部预算不改，不提供相反事实/正确页/动作。f01当前蓝框上主judge仍错误支持nocue，但独立focus读蓝框，新一致性会withhold；这不是主judge修好/完整GUI成功。f02/f03为人工WAIT按用户口径排除，不是自然actorWAIT。其余仍以新终局原始回执为准。

另一个输入分支覆盖focus_reason的CPU漏洞已在独立linkedcopy复现：相同负面cue+type原误accepted，修复为保留先前conflict后blocked；正常positive typing仍eligible。focus-conflict-typing-edge-development/current.json，2行为回归通过，0新推理；不改正在运行release/source seal。完整GUI候选将使用v4.0.3a，在本诊断独立审查/actualservice全绑定通过后才进入新原预算GUI，不能把工程测试当真实成功。风险：独立reader也会错、保守暂扣可误拦并消耗原预算；窄规则可能漏改述，未命中不是semantic批准。

上一focus-history-fullgui终局仍是official1但blocked/regeneration_cap，有已执行蓝框错读及计划误作完成；绝不重复launch/花未用总cap重试。原27B服务UID1033/5GPUlocks/service.lock和actualrequests已核实，当前推理时health延后不是故障；不重启服务、不碰外资源/GPU5/6/7。旧27B注意力已终局，勿信下方旧未启动快照。其余60native/live adapters/自然WAIT/loading阳性/完整正式效力仍未完，monitorACTIVE。

--- 以下为历史交接 ---

'''
out=PREP/('progress-handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw)
    p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8')
    rows.append({'path':str(p),'backup':str(backup),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'monitor':'ACTIVE','phase':'running_diagnostic'},indent=2))
print(json.dumps({'backed_up_handoffs':3,'directory':str(out),'monitor':'ACTIVE'}))
