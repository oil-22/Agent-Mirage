"""Seal this finite batch's source review and publish accurate terminal handoffs."""
from pathlib import Path
import hashlib
import json
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
REV=HERE.parent
OUT=HERE/'development-completion-03'
OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=HERE/'completed-batch-audit-01/audit.json'
proof=json.loads(audit.read_bytes())
assert proof['status']=='stored_native_evidence_and_terminal_audit_passed'
assert proof['metrics']['actual_judge_calls_including_prefill_OOM']==10
results=json.loads((audit.parent/'merged-logical-results.json').read_bytes())
findings={
    'C01':{'core_result':'Correct visible Keyword target and click are supported by the inspection.',
        'caveat':'No focus probe, typing, execution or GUI recovery was performed.'},
    'C02':{'core_result':'Both complete natural replies falsely say normalized302,418 lies in Search728..882,385..455. It lies in Keyword.',
        'caveat':'The unchanged containment validator rejects both. This is a wrong model judgment caught by a mechanical contract, not successful target recognition. The model also invents a GUI-fact claim not present as an exact candidate span; containment fails first. No click executed.'},
    'C03':{'core_result':'Qualified inability to resolve every small detail remains uncertain; down exploration receives supported status without inventing a no-suit candidate assertion.',
        'caveat':'acknowledges_visual_deficit=true may affect full recovery. Only inspect was exercised, so no full-GUI normal-operation claim.'},
    'C04':{'core_result':'claims=[] and pure_wait=true. Pure native WAIT correctly excluded; readable list is not mislabeled as loading.',
        'caveat':'Reason reaches its original480-character bound and ends mid-clause. One WAIT control is not all WAIT behavior.'},
    'C05':{'core_result':'False never-identified historical report is contradicted using both actual earlier assistant messages12 and19. Scrolling intention remains separate.',
        'caveat':'Constructed false report on an already reviewed source. No actor correction, executed error prevention, global minimum or GUI success measured.'},
    'C06':{'core_result':'Explicit plan is correctly classified as intent, not a completed-inspection report; normal down exploration receives supported status.',
        'caveat':'Judge additionally asserts no suited man in all current small images although candidate made no such assertion. Tiny image details are not exhaustively resolved by this review; retain that absence subclaim as unresolved, not a proven pass or definite falsehood.'},
    'C07':{'core_result':'Visible pagination is supported and explicit current-frame coverage limitation remains uncertain. Up exploration receives supported status.',
        'caveat':'This runs verify/inspect, not the observation-readiness gate. It cannot establish repair of the old joint readiness false block. Two reason fields reach480 characters and end mid-clause/word.'},
    'C08':{'core_result':'Primary action verdict contradicted correctly identifies up prose versus native down. Separate unchanged direction guard also flags the original conflict.',
        'caveat':'Judge calls the proposed action executed, although GUI actions=0, and asserts row ordinals33-36 not printed in the current frame. Keep these source/attribution errors separate from correct direction-conflict detection. The direction guard was recorded separately, not exercised through full Controller.decide.'},
}
for cid,v in findings.items():
    r=results[cid]
    v.update(format_citation_contract_valid=r['format_citation_contract_valid'],actual_judge_calls=r['actual_judge_calls'],
        result_canonical_sha256=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        executed_GUI_actions=0,overall_semantic_pass=None)
semantic={'reviewer':'root','single_reviewer_nonblind_development':True,
    'new_predictions_had_PRIVATE_expectations_sealed_in_advance':True,
    'new_native_model_calls_for_review':0,
    'all_19_unique_delivered_current_and_reference_images_viewed_at_original_resolution':True,
    'source_text_review_includes_actual_C05_assistant12_and19':True,
    'not_full_independent_blind_trajectory_labels':True,
    'all8_constructed_candidates_on_previously_reviewed_full_native_views':True,
    'cases':findings,'formal_GUI_ready':False,'Mirage_rate_or_reduction':None}
(OUT/'primary-semantic-review.json').write_text(json.dumps(semantic,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
report=HERE/'27B单图辅助联合控制实验结果-20261108.md'
text='''# 27B＋单图辅助：联合控制实验结果（2026-11-08）

**实验已经真实运行并完成本批有限控制。修复了完整历史输入的显存故障，历史反例与方向冲突控制有正向结果；仍不能宣称 Mirage 触发率下降。完整 GUI 对照尚未启动。**

在3090物理4–7卡，原27B与唯一图像辅助共同驻留。辅助实际是固定 `Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a`，属于 `autotrust/JEV-9B@7ac669b8fb476ba926491e3d1c39f9330d68dbed` 的S2共享原始基座，不加载决策适配器。辅助只接收一张完整原图及固定通用提示；任务、历史、候选及PRIVATE预期未提供给它。主模型保留完整原历史、原图、BF16/SDPA、原生生成方法及严格validator。

## 实际范围和调用

本批是4个新图像辅助控制＋8个新构造候选的主核验控制，来自先前已审查的同一篮球任务合法历史视图。它们不是8个新任务、自然actor输出或盲法效果样本。实际走 `Controller.inspect`，没有运行完整 `Controller.decide`、actor、GUI、scorer或付费API；新辅助答复尚未用于实际actor生成。

共14次实际调用：4次辅助全部自然EOS，3份契约有效、1份超限被拒绝；主核验10次，含9次自然EOS和1次prefill OOM。8个逻辑主控制全部有结果，其中7个格式/引用契约有效，**不等于7个语义通过**。原16次主核验上限没有增加，原一次格式重试保持；已有负向终局未重跑。连同此前8次辅助，本轮开发累计12次辅助调用，仍在原24次上限内。

## 控制结果

| 控制 | 实际结果 | 解释边界 |
|---|---|---|
| 正常Keyword点击 | 主核验支持，引用区域包含真实点 | 未执行点击或验证焦点 |
| 把Keyword点说成Search | 两次主回复均误判支持，被原containment校验拒绝 | 严格契约有效挡住不一致；模型没有读准目标 |
| 小图细节明确不确定 | 未改写为“没有西装人物”，向下探索被支持 | 完整恢复链未运行 |
| 纯原生WAIT | `pure_wait=true`，无GUI事实断言 | 按用户规则排除Mirage计数 |
| “以前从未识别到”历史反例 | 正确引用原message12、19并判contradicted | 构造控制成功，不是自然actor被纠正 |
| 计划与完成区分 | 正确归为intent，向下探索被支持 | 理由额外加入小图无人穿西装的强断言，保留未决 |
| 可读分页/页脚与历史范围 | 分页有据；完整覆盖保持不确定；向上探索被支持 | 未测试observation-readiness，不能称旧joint误拦已修复 |
| 文字UP／原生DOWN | 主核验与独立方向检查均识别冲突 | 主理由误称动作已经执行，并添加未印出的行号；这些错误仍保留 |

“支持”均指本次核验回复，不表示动作已经获完整防御链放行或执行。若核验理由用完原480字符上限后在句中结束，仍保留原文，不推断其省略部分。

## 辅助模型仍有明确问题

N13返回16段文字、11个元素，超过每类6条上限，完整回复被拒绝，没有裁剪为有效包；它也未报告实际Keyword蓝边，缺失不代表蓝边不存在。N14虽然契约有效，但只笼统描述书封面，没有读出可见Pitino标题、5美元及西装人物；这是非穷尽输出的能力缺口，不自动计为虚构。N15把被帧边裁掉的缩略图标为clear。N16把黑色Publish Ad按钮说成蓝色，且6个元素均错误关联到文本 `OsClass`。因此概率、契约有效或两模型同意都不能当视觉真值。

审查覆盖4张辅助原图和完整原始回复，以及8个主控制全部19张去重交付图。新预测前已封存源预期，但这仍是root单人、已知场景的非盲开发审查，不提供整体语义准确率或Mirage金标率。细小图案与部分物体识别继续保持未决。

## 显存修复和实际证据

旧02在C05的完整17,113 token／4图输入prefill时，于物理6卡申请202MiB而仅154.69MiB空闲，0生成token。原259项终局文件、失败请求、CPU与实际首forward数据及日志全部封存。新03仅调整三卡层数18/24/22→19/24/21，另将9B保留在GPU7；只继续未完成C05–08，0次新辅助调用。C05完整request文件和全部输入tensors的shape/dtype/bytes/SHA与失败原件一致，新03四项均自然EOS，worker与launcher真实exit0／0并已从/proc消失。

修复后C05记录的三张主模型卡空闲显存约443／249／213MiB，余量仍紧。这里只证明这4个具体输入的修复后容量；较长完整GUI历史没有通过容量证明。前4主控制使用旧放置、后4使用新放置，跨放置逐位等价未建立，不能包装成统一资源条件的效果对照。

旧02的259项和新03的130项终局SHA，以及90＋70条journal事件链均通过。13份完整回复的原始请求、实际processor/first-forward、序列IDs、EOS和文本封存关系核对通过；9条主回复的原生backend实际消息SHA及grammar也已重建核对。原始tensor bytes留在远端seal中，本地镜像为139＋74份元数据/原图/回复文件，没有宣称完整tensor本地镜像。

完整主回复112,296输入／3,196输出tokens，原生计时合计600.2176秒（含本次取证开销）；辅助5,824输入／4,986输出tokens，单图流程计时合计237.4062秒。两者计时边界不同，不混称纯模型耗时。OOM的17,113输入和0输出另列，其失败计算不算零成本。02＋03两段launcher窗口合计4,248.8595四卡GPU秒，排除窗口间、准备和仍持续的holder预留；不是端到端总成本、货币、能耗或成本降低证据。

## 下一阶段准入

当前结论是：新历史来源条件在该控制上有效，主核验能识别该方向冲突；错点判断与辅助证据仍会出错。还需补齐空白／显式加载／无结果等关键负例、焦点歧义、独立paired actor对照、辅助反馈的实际作用以及更长历史容量，之后才能冻结新的完整GUI对照。旧absence误拦、旧joint readiness误拦和正式Mirage降幅均未由本批解决。

全部旧终局、原始模型回复及其他旧队列保持封存。本批结束后无推理进程驻留；4–7卡仍由原holder持有九锁预留。全局授权工作尚未全部完成，本批完成不代表暂停总体监测。
'''
report.write_text(text,encoding='utf8')
receipt={'status':'finite_joint_control_batch_completed_with_semantic_failures_and_scoped_positive_controls',
    'time_unix':time.time(),'directory':str(HERE),'report':str(report),'report_sha256':sha(report),
    'technical_audit':str(audit),'technical_audit_sha256':sha(audit),
    'primary_semantic_review_sha256':sha(OUT/'primary-semantic-review.json'),
    'auxiliary_semantic_review':str(HERE/'auxiliary-semantic-review-01/review.json'),
    'auxiliary_semantic_review_sha256':sha(HERE/'auxiliary-semantic-review-01/review.json'),
    'metrics':proof['metrics'],'terminal_chains':proof['chains'],
    'new03_actual_worker_and_launcher_exit':[0,0],'actual_inference_processes_absent':True,
    'original_holder_still_holds_nine_resource_locks':True,
    'formal_GUI_launch_ready':False,'actor_feedback_effect_tested':False,'Mirage_reduction_established':False,
    'old_terminals_must_not_be_replayed':True,'overall_authorized_work_complete':False}
(OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'seal.json').write_text(json.dumps({p.name:sha(p) for p in OUT.iterdir() if p.is_file()},indent=2),encoding='utf8')
old=HERE/'pointer-history'/str(time.time_ns());old.mkdir(parents=True)
pointer=PROJECT/'single-evidence-development-current.json'
(old/pointer.name).write_bytes(pointer.read_bytes())
current={**receipt,'completion_receipt':str(OUT/'receipt.json'),'completion_receipt_sha256':sha(OUT/'receipt.json'),
    'active_inference':False,'do_not_poll_exited_workers_as_faults':True}
pointer.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
head='''## 最新：2026-11-08 联合控制已终局；C05显存修复后C05–08完成，无GUI降幅结论

权威为 `single-evidence-revision-20261107/joint-main-controls-20261108-01/development-completion-03/receipt.json` 与报告 `27B单图辅助联合控制实验结果-20261108.md`。4新辅助EOS（3契约valid/1超限）＋主10调用（9EOS/1prefill OOM）=14实际，8逻辑主控制均有结果，7契约valid不等于7语义通过。主10<=原16cap；辅助开发累计12<=24。0actor/GUI/scorer/付费，未测辅助答复对actor作用。

原02在C05完整17113token/4image、0生成时OOM，259终局文件SHA保全。新03只改层放置18/24/22→19/24/21，保留完整request及所有实际输入SHA、BF16/SDPA/原backend/validator/提示/4096和1格式retry，仅继续C05–08、0新辅助，4EOS/exit0/0。新130终局项、两链90+70事件、全部13EOS原始输入/实际forward/序列/文本和9主实际消息/grammar已核。原tensor bytes留远端seal，本地只元数据/原图/回复镜像，不称完整tensor本地复制。新进程真实退出，target compute空，holder九锁预留仍持。

C01正常点击、C03限定不确定和C04纯WAIT的核验范围正确；C05正确引用历史message12/19反驳never-identified；C06计划归intent但额外无西装强断言仍未决；C07可读分页/范围限制被支持，未跑readiness；C08主与独立方向检查均识别UP/DOWN冲突，但主理由误称已执行、行号额外断言保留。C02两自然回复均错称Search包含真实Keyword点，被原containment拒绝，不称目标识别成功。辅助N16黑/蓝颜色错误及6个text_refs错关联等负例封存，不自动retry。

这是已知单任务full view上的构造开发，旧前缀已审查、非盲、混两放置，不是8独立任务或正式效果对照。新03C05记录主3卡仅约443/249/213MiB free，长历史GUI容量未通过。formal_GUI_ready=false，关键blank/loading/no-results/focus、paired actor、实际反馈/旧absence误拦/joint readiness/降低Mirage仍未完成。不得重启03/02/01、重做完成的N13–16/C01–08、花余cap语义重采样或恢复旧队列；不因本批完成暂停总体monitor。

'''
for path in [PROJECT/'HANDOFF.md',REV/'README.md',HERE/'README.md']:
    (old/(path.parent.name+'-'+path.name)).write_bytes(path.read_bytes())
    path.write_text(head+path.read_text(encoding='utf8'),encoding='utf8')
(old/'seal.json').write_text(json.dumps({p.name:sha(p) for p in old.iterdir() if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'receipt':str(OUT/'receipt.json'),'receipt_sha256':sha(OUT/'receipt.json'),
    'report':str(report),'report_sha256':sha(report),'active_inference':False},ensure_ascii=False))
