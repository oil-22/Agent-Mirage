"""Record explicit user approval, resource wait and the existing monitor update."""
import ast
import hashlib
import json
import time
import tomllib
from pathlib import Path

BASE=Path(__file__).resolve().parent;PREP=BASE/'uitars-verifier-preparation';ATT=BASE.parent/'crossmodel-injection-attention-20261025'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=json.loads((PREP/'dual-gpu-staging.json').read_bytes())
auth=json.loads((PREP/'dual-gpu-user-authorization-20261027.json').read_bytes())
resource=json.loads((PREP/'dual-gpu-resource-current.json').read_bytes())
assert resource['state']=='waiting_resources'
assert not(PREP/'dual-gpu-launch.json').exists()
out=PREP/('dual-gpu-authorization-handoff-'+str(time.time_ns()));out.mkdir()
files=['uitars_dual_gpu_preflight.py','prepare_uitars_dual_gpu_20261027.py','launch_uitars_dual_gpu.py','inspect_uitars_dual_gpu.py','uitars_dual_resource_guard.py','test_uitars_dual_resource_guard.py']
for name in files:ast.parse((BASE/name).read_text(encoding='utf-8'))
checks={'resource_boundary_tests_passed':12,'all_new_scripts_parse':True,'worker_sha256':sha(BASE/'uitars_dual_gpu_preflight.py'),
 'unchanged_backend_and_validator_bytes_verified_during_staging':True,'original_single_gpu_seal_revalidated':True,
 'staged_manifest_sha256':stage['staged_manifest_sha256'],'model_calls':0,'gui_actions':0,'semantic_pass_claimed':False}
(PREP/'dual-gpu-preparation-verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
text=f'''# UI-TARS双GPU完整输入预检：用户已授权，等待资源（2026-10-27）

用户明确选择：“{auth['user_reply']}”。该授权已保存到`dual-gpu-user-authorization-20261027.json`，替代先前“等待用户选择”的状态。原单24GB组的两次OOM、20项开发控制及其封存结果仍保留。

新组独立暂存于`{stage['root']}`。它先只检查`long-history-candidate`：原39,598输入token、22张原图、完整合法历史、固定官方权重revision683d002dd99d8f95104d31e70391a39348857f4e、BF16/SDPA、原native processor/核验提示/JSON grammar/4096输出上限及严格validator。使用两张独占RTX4090，balanced模型放置；最多2次调用（原一次格式重试），没有27B fallback、GUI、actor、评分或付费API。旧短控制的失败不重跑；新组终局也不自动加预算/加卡重试。

改变的实验条件是GPU数量与模型跨卡放置。新结果分别报告，不能覆盖单卡失败；跨卡数值运行也不预先宣称与单卡输出逐位相同。容量通过不修复已发现的语义问题，不自动放行正式UI在线组。

费用口径使用**两张被占用的GPU**，记录各卡peak allocated/reserved、加载及生成延迟、调用数和2×占卡时长；各卡各自峰值之和不是同时峰值。没有实测价格/功率就不报告货币/能耗，也不预先宣称比27B端到端便宜。

当前资源检查：4090物理GPU3空闲，GPU1仍有UID1001的其他用户进程；GPU0/2也有其他用户进程。3090自有卡承载现有27B服务，不为本组抢占。资源门禁拒绝启动：GPU1有进程且空闲显存不足阈值。此次0模型调用、0GPU推理分配。双卡尚未加载模型，未证明能容纳该输入。

资源门禁12项CPU边界测试通过，包括外部小CUDA上下文、自有旧任务、缺卡/错卡、显存不足、查询失败、错UID/缺锁，全部拒绝共享或抢占。原单卡完整封存再次核验；实际backend/core/prompts/schema与sealed parent逐字节相同，新worker的status/validate/format_feedback AST不变。暂存manifest SHA`{stage['staged_manifest_sha256']}`，worker SHA`{checks['worker_sha256']}`。这些是静态准备验证，不是真实双GPU预检成功。

后续由现有两小时巡检继续：先`inspect_uitars_dual_gpu.py`，若尚未launch且有两张合法可独占空闲卡，再运行带原子启动锁和持久active回执的`launch_uitars_dual_gpu.py`。启动前重新核对UID/完整进程命令、全部compute进程、两卡显存及两把任务锁；任一卡有进程均等待，不停止任何外部服务。回执存在后只inspect，禁止重复launch。保留新组全部输入IDs/图grid、回复/失败、逐卡显存/延迟、日志/源码/产物SHA；终局后独立审查实际合法输入与回复。当前无需用户再次确认这一双GPU条件。
'''
report=BASE/'UI-TARS双GPU完整输入预检设定与资源等待-20261027.md';assert not report.exists();report.write_text(text,encoding='utf-8')
header=f'''# 最新2026-10-27：用户已授权UI双GPU预检，独立暂存完成，当前等待第二张空闲卡

用户回复“{auth['user_reply']}”，权威`uitars-verifier-preparation/dual-gpu-user-authorization-20261027.json`。不再是待用户选择；不要重复询问。独立暂存root`{stage['root']}`，`dual-gpu-staging.json`，manifest SHA{stage['staged_manifest_sha256']}；报告`UI-TARS双GPU完整输入预检设定与资源等待-20261027.md`。原20单卡终局和两次OOM保持原样，新组不覆盖它们。

新双卡条件先仅long-history-candidate：39598token/22原图/完整历史/固定revision/BF16/SDPA/原processor/提示/grammar/4096输出/strictvalidator，最多2调用（原1format retry），无27B fallback/GUI/actor/评分/paidAPI。只改两卡balanced placement，按双卡记录成本，不能预设跨卡输出逐位一致或显存通过就语义通过/正式放行。原短控制不重跑，新组终局也不能自动加预算或重试。

当前资源门禁waiting_resources（dual-gpu-resource-current.json）：4090仅GPU3空闲，拟用GPU1有UID1001进程且free23022MiB<门限；GPU0/2也有他人进程。未抢占3090防御服务或其他用户，0模型调用/0GPU推理分配。12项资源边界测试通过、原单卡封存复核、backend/core/prompts/schema字节一致，静态准备不等于真实双GPUfit。先inspect_uitars_dual_gpu.py；尚未launch且资源重新满足才用launch_uitars_dual_gpu.py，持startup锁/两卡任务锁/持久active回执，已有回执绝不重复launch。实际UID/完整命令/锁/请求回复/inputIDs/图grid/显存/日志SHA核对，失败完整保全，全部语义还需独立审查。记录逐卡peak、加载/生成秒及2×占卡秒，不冒称货币能耗/端到端省成本。

原542候选审阅结果保持封存；其它60原生完整在线预检、原27B注意力、joint正常页脚readiness诊断仍待办；monitor继续ACTIVE、旧机制暂停。不要因资源等待把本组当失败或重启任何旧UI/attention/终局队列。

--- 以下为历史交接 ---

'''
for p in [BASE/'README.md',BASE/'REPAIR_HANDOFF.md',ATT/'HANDOFF.md']:
 raw=p.read_bytes();(out/(('attention-'if p.parent==ATT else'defense-')+p.name)).write_bytes(raw);p.write_bytes(header.encode('utf-8')+raw)
auto_path=Path('C:/Users/researcher/.codex/automations/mirage/automation.toml');raw=auto_path.read_bytes();(out/'automation-before.toml').write_bytes(raw);auto=tomllib.loads(raw.decode('utf-8'))
prompt=auto['prompt'];start=prompt.index('One user deployment-choice question PENDING:');end=prompt.index('\n\nEarlier initial UI load root',start)
new='''User HAS EXPLICITLY AUTHORIZED a NEW independent dualGPU preflight: “另设双 GPU 预检，保留完整输入和 BF16，并按双卡计算部署成本”. Authority uitars-verifier-preparation/dual-gpu-user-authorization-20261027.json; no pending choice/reasking for this condition. Original singleGPU20results/twoOOMs remain immutable. New staged root /data/researcher/mirage-defense-pilot-20261023/uitars-dual-gpu-staged-1793113663066728448; dual-gpu-staging.json manifest33813426afe96223a90992d802327ec79bf44fe982058526cd8d11e879b1a3bc. Worker765e4ed55f36fbf3df8572e26d7e6728b48784046d26c130bb6320abf5ad9941. Report UI-TARS双GPU完整输入预检设定与资源等待-20261027.md. Only long-history-candidate original39598tokens/22images/fullhistory/fixedrevision/BF16/SDPA/nativeprocessor/prompts/grammar/4096output/strictvalidators, at most2calls(original1formatretry). New twoGPU balanced placement; cost counts TWO reservedGPUs, per-device peaks/load-generationlatency/2xreservedseconds, no invented currency/energy/endtoend savings or guaranteed single/dual bitwise outputs. NoGUI/actor/scoring/paidAPI/27Bfallback. Short old failed controls not rerun; new terminal not auto retried or budget expanded. Capacitypass does not resolve existing semantic failures or release formalUI.

Current dualGPU state waiting_resources,0modelcalls/0GPUinferenceallocation.4090GPU3 free but proposedGPU1 has foreignUID1001process/free23022MiB;GPU0/2also foreign; do not share/preempt/stop them or3090defense service.12CPU resource-boundary tests passed; original failure seals and exactbackend/core/prompts/schema copied/verified. These are STATIC preparation, not dualGPU memory success. Read dual-gpu-resource-current.json and inspect_uitars_dual_gpu.py first. If no active receipt and TWO task-allocatable freeGPUs are verified again, launch_uitars_dual_gpu.py uses atomicstartup/twoGPUsinheritedlocks/persistentactive receipt; otherwise stayquiet waiting. It currently proposes physical3,1 with both noexistingcomputeprocess and>23500MiB free, expectedUID1015tasklocks. Never rerun any old UI queue. Once dual-gpu-launch.json or remote uitars-dual-gpu-active.json exists, inspect actualUID/fullcommand/locks/logs/realrequestsreplies/inputIDSHAs/imagegrids/perdevice memory/terminalSHAs; no duplicate launch. Completed new failures preserve all before diagnosis; no smaller input/precision/budget change. Keep monitorACTIVE for dualGPUresourcewait plus60native/original27Battention/jointreadiness. No new confirmation needed for this approved twoGPU condition.'''
prompt=prompt[:start]+new+prompt[end:]
payload={'mode':'update','id':auto['id'],'kind':auto['kind'],'name':auto['name'],'prompt':prompt,'rrule':auto['rrule'],'status':auto['status'],'targetThreadId':auto['target_thread_id']}
if 'notification_policy'in auto:payload['notificationPolicy']=auto['notification_policy']
target=BASE/'automation-update-uitars-dual-approved-20261027.json';target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest={'authorization_record':str(PREP/'dual-gpu-user-authorization-20261027.json'),'state':'waiting_resources','model_calls':0,
 'tests_passed':12,'staged_root':stage['root'],'resource_snapshot':resource['snapshot'],'automation_update_pending':True,
 'files':{str(p.resolve()):sha(p)for p in [report,target,*[BASE/n for n in files],PREP/'dual-gpu-user-authorization-20261027.json',PREP/'dual-gpu-staging.json',PREP/'dual-gpu-static-proof.json',PREP/'dual-gpu-resource-current.json',PREP/'dual-gpu-current.json',PREP/'dual-gpu-preparation-verification.json',BASE/'README.md',BASE/'REPAIR_HANDOFF.md',ATT/'HANDOFF.md',*[x for x in out.iterdir()if x.is_file()]]}}
(PREP/'dual-gpu-authorization-artifacts-20261027.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(report),'state':'waiting_resources','tests':12,'model_calls':0,'automation_payload':str(target)}))
