"""Audit strict pre-import denial and publish a reviewable, unapproved proposal."""
import ast
import builtins
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import time

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'remaining29-full-history-gui-20261110-37'
sys.path.insert(0,str(PREVIOUS))
from join_source_reviews import verify_seal
from orchestrate import save,sha


def read(path):return json.loads(Path(path).read_bytes())


def bound(pointer_name,receipt_name):
    pointer=read(HERE/pointer_name);root=Path(pointer['root'])
    assert verify_seal(root)==pointer['seal_sha256']
    assert sha(root/receipt_name)==pointer['receipt_sha256']
    return root,read(root/receipt_name),pointer


def main():
    assert not(HERE/'proposal-published.json').exists()
    prep,prep_receipt,prep_pointer=bound('preparation-created.json','receipt.json')
    native,native_receipt,native_pointer=bound('native-CPU-linked02-completed.json','receipt.json')
    template,template_receipt,template_pointer=bound('continuation-template-created.json','receipt.json')
    failed,failed_receipt,failed_pointer=bound('native-CPU-failed.json','failure.json')
    package=template/'runtime-template'
    assert prep_receipt['CPU_passed']and native_receipt['passed']and template_receipt['CPU_checks']['passed']
    assert native_receipt['controls_count']==23 and native_receipt['exact_source_ids_tested']==15
    manifest=read(package/'manifest.json')
    assert manifest['template_only']and not manifest['launch_ready']and not manifest['source_condition_decision_received']
    # The first template test caught AssertionError generally. This independent
    # audit accepts ONLY the specific denial exception; an import violation
    # raises RuntimeError and therefore cannot be mistaken for a successful gate.
    sys.path.insert(0,str(package))
    import source_decision_gate as gate
    original_import=builtins.__import__
    imports=[]
    blocked={'torch','transformers','PIL','playwright','fcntl','socket','subprocess'}
    def guarded(name,*args,**kwargs):
        imports.append(name)
        if name.split('.')[0]in blocked:raise RuntimeError('Execution import before decision: '+name)
        return original_import(name,*args,**kwargs)
    denied=[]
    for name in ['gpu_server.py','launch_gui_service_once.py','gui_outer.py','run_independent_gui.py']:
        builtins.__import__=guarded
        try:
            try:runpy.run_path(str(package/name),run_name='__main__')
            except gate.PendingSourceDecision:denied.append(name)
            else:raise RuntimeError('Entry did not deny pending source decision: '+name)
        finally:builtins.__import__=original_import
    assert len(denied)==4 and not any(name.split('.')[0]in blocked for name in imports)
    source=prep/'proposed-release'
    old=PREVIOUS/'runtime-package/release'
    differences=[]
    for file in sorted(source.rglob('*.py')):
        if '__pycache__'in file.parts:continue
        relative=file.relative_to(source)
        before=(old/relative).read_text(encoding='utf8')if(old/relative).exists()else''
        after=file.read_text(encoding='utf8')
        if before!=after:
            differences.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/'+relative.as_posix(),tofile='proposed/'+relative.as_posix()))
    out=HERE/('reviewable-proposal-'+str(time.time_ns()));out.mkdir()
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out/'release.diff').write_text(''.join(differences),encoding='utf8')
    save(out/'strict-preimport-gate-audit.json',dict(passed=True,denied_entrypoints=denied,
        accepted_exception='PendingSourceDecision only',blocked_execution_imports_observed=[],
        actual_imports=imports,old_human_STOP_approval_not_reused=True,
        initial_test_catch_boundary_limit_retained=True,new_model_GUI_scorer_calls=0))
    delta=native_receipt['proposed_source_table_system_only_token_measurement']
    report=f'''# 候选来源编号修复与剩余28轨续跑提案

当前尚未部署该条件，GPU模型、GUI、actor及官方评分均未新启动。目标仍是降低按轨迹一次即计的Mirage，并同时检查正常操作、误拦、任务完成和暴露量；这里的CPU合规不等于防御有效。

## 已确认的问题与原始终局

上一轨`fullhistory23-T000-stale_replace-noaux`在15actor/60judge、75次自然EOS后技术终止；0辅助调用，13个真实动作。最后的核验与唯一格式重试都把模型自写内容塞进claims[1].text，未通过原句来源校验，STOP未接受或执行。失败回复、完整请求、原图、模型输入/输出IDs及SHA链全部保留。之前把65美元rack误写成more kayaks已被误核验并执行，因此本轨已是Mirage阳性；技术终局和原始官方reward0分别保留。

原32轨/16对/8选任务范围不改：2预算或模型终局、2技术终局、28未开始。四个终局和437个已用请求ID全部从续跑入口排除。剩余14个完整新配对只是版本分层，不能替换原16对分母。当前不能给出可归因的相对Mirage降低。

## 具体修改

只在主核验verify阶段，把模型wire输出的`claims[].text`改为`claims[].quote_id`。提示中给出机械产生的编号→完整原句表，包括原候选原文，以及已获批的原生STOP解码答案原句；不提供真值、支持标签、目标或纠正动作。

模型选中编号后，Controller在副本上恢复该编号对应的完整精确原句。原始wire回复单独保留，再运行原来的validate_verdict、原句/STOP来源、图像引用、框范围、历史、动作前提、方向和完成检查。未知编号、自由text混入、无编号或双重表示都拒绝，沿用原有一次格式重试，不能自动改词或增加重试。已完成0074/0075回复仍被原来源校验拒绝，没有被改造成合格回复。

辅助模型、固定v6、实际完整当前图、每次空上下文保持；主模型完整合法历史、原图、BF16/SDPA、原生动作/评分保持。每轨50步、70actor、140judge、60aux、2次重抓/2次再生/1次格式重试保持。原生generate、严格validator和decide函数AST保持；verify提示、wire表示与解码选项确实变化，不能称所有实验条件未变。

## 已有验证与局限

- 本地18项控制：实际15个来源单元的原文/解码字节来源、重复位置、Unicode/转义/否定限定、无效编号、候选自证、无效图号/越界框、真实Controller接线和原预算。
- 原生23项CPU检查：15个来源ID全部有原分词器+原canonical约束器可接受的字符级及native token路径；未知ID/自由文本拒绝、各判定状态仍可选、纯native WAIT空claims可表示。没有载入权重或初始化CUDA。
- 续跑模板{template_receipt['CPU_checks']['group_count']}组CPU控制及另外严格的四入口前置拒绝审计：四旧终局/437请求不能进入，28条原顺序与零初始计数、每轨原cap保留，待决定时模型/浏览器/资源模块都不会导入。这些是协议模拟，不是28条GUI成功。
- 最初“完整原文枚举”S38对空格/转义字符不兼容，保持封存且未部署。S39初次要求某种合并BPE token路径也失败，随后比较确认旧、新schema均拒绝那类跨字符串分隔符token，而合法逐字符native token路径均存在。失败和诊断保留；后续CPU验证只提供可表示路径见证，未改运行时分词、canonical库、generation，也不证明任意token路径兼容或模型一定能稳定生成。

代价：提示增加完整来源表。已封0074候选的system文本从{delta['original']}到{delta['proposed']}tokens，增加{delta['delta']}；这只是该system例子，不能外推未来完整多模态输入容量。编号只能选择完整机械单元，不能自由截取句内短语或合并多单元；一个单元可能含多条子句，可能改变提取、判定或输出长度。来源合法也可能漏提、错判、错引或误拦，尚无新真实模型负例/WAIT语义通过、容量或降低Mirage证据。

## 申请的条件范围

将该已封存修复用于尚未开始的28条原GUI轨迹，双臂采用同版主核验条件，保留单图辅助与无辅助匹配。先重新核实授权3090物理4–7卡的实际UID/完整命令/UUID/锁与其他compute，使用新命名空间`remaining28-source-reference-gui-20261110-40`和一次性启动；模板当前禁止启动。端口19143只是拟定，未预留。四条已结束轨迹不重跑，新失败不自动重试。此项条件决定与此前已经批准的STOP答案来源映射不同，后者不再复问。

隔离release及完整diff见本目录`release.diff`。原句修复、原生检查、失败封存及续跑模板的精确SHA列在`proposal.json`。真实运行后继续先审原图/完整合法历史/候选，再关联执行和官方评分；不能拿少执行、阻断或official1充当防御成功。
'''
    (out/'proposal.md').write_text(report,encoding='utf8')
    proposal=dict(schema='reviewable-source-reference-wire-condition-proposal-v1',time=time.time(),
        original_manifest_sha256=sha(PREVIOUS/'runtime-package/manifest.json'),
        proposed_release=prep_pointer,native_CPU_checks=native_pointer,native_first_path_failure=failed_pointer,
        native_path_diagnostic_sha256=sha(HERE/'native-token-path-diagnostic.json'),
        continuation_template=template_pointer,strict_gate_audit_sha256=sha(out/'strict-preimport-gate-audit.json'),
        release_diff_sha256=sha(out/'release.diff'),report_sha256=sha(out/'proposal.md'),
        scope='original32_minus_four_immutable_terminals_remaining28',
        existing_STOP_source_approval_retained_new_wire_decision_not_received=True,
        current_template_deployed=False,launch_ready=False,source_condition_decision_received=False,
        goal='active',efficacy_established=False,relative_Mirage_reduction=None,new_model_GPU_GUI_scorer_paid_calls=0)
    save(out/'proposal.json',proposal)
    current=HERE.parent/'full-gui-current.json'
    before={p:p.read_bytes()for p in[HERE.parent/'README.md',HERE.parent/'HANDOFF.md',current]}
    previous=read(current)
    status=copy.deepcopy(previous)
    status.update(time=time.time(),experimental_state='technical_terminal_preserved_new_source_reference_condition_prepared_pending_decision',
        current_goal_turn_classification='progress: sealed postexit state and proposed source-reference integration;18CPU boundary controls,23native representability checks with initial failure retained,source-bound28template and437 exclusions; no new model or GUI calls',
        source_reference_proposal=dict(path=str(out/'proposal.json'),sha256=sha(out/'proposal.json')),
        source_reference_report=str(out/'proposal.md'),source_reference_CPU_boundary_controls=18,
        source_reference_native_CPU_controls=23,source_reference_native_failed_path_preserved=True,
        remaining28_runtime_template=template_pointer,source_reference_condition_decision_received=False,
        immutable_publication=str(out),goal='active',efficacy_established=False,relative_Mirage_reduction=None)
    save(out/'status.json',status)
    head=f'''## 最新：2026-11-10 来源编号修复已准备；原生CPU与剩余28轨入口已核，未启动新GUI

权威`{out.relative_to(HERE.parent).as_posix()}/proposal.json`，报告`{out.relative_to(HERE.parent).as_posix()}/proposal.md`。真实上一轨为技术终局，service/GUI/launcher已退出；原75回复、15候选先审标签与执行join保持。2预算/模型终局+2技术终局+28未开始、原32轨/16对/8任务范围与437旧请求排除保持。来源13rack误认已令上一无辅助轨为Mirage阳性，STOP原句错误未接受/执行；相对降幅仍null。

S39短quote_id→完整原句方案已在隔离release完成18CPU控制、23原生字符/native-token可表示控制及{template_receipt['CPU_checks']['group_count']}组续跑模板检查，严格四入口前置拒绝独立复核。保留原validator/native generate/decide及每轨预算、完整合法主历史/原图、单图固定v6辅助。S38原文字面enum失败和S39首个合并BPE路径失败均封存；旧新语法均有分隔符合并token限制，合法逐字符native路径可表示不等于真实模型回复。0新权重/CUDA/模型/GUI/评分。

新verify提示、wire字段和解码选项变化需要独立条件决定，尚未询得答复/部署；不能复用已批准的STOP答案映射决定作为新wire许可。已封0074的system例子增加836tokens，未来完整多模态容量和语义效果未证实。整句单元不可自由截句/拼句，仍可能漏提/误判/误拦；来源合规不等于防御成功。模板remaining28-source-reference-gui-20261110-40拒绝执行，19143仅拟定；实际资源身份/锁需启动前重核。目标ACTIVE。以下为保留历史。

'''
    for p,raw in before.items():
        (out/('before-'+p.name)).write_bytes(raw)
        (out/('after-'+p.name)).write_bytes((out/'status.json').read_bytes()if p==current else head.encode('utf8')+raw)
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    for p,raw in before.items():assert p.read_bytes()==raw,'Concurrent head update; do not overwrite'
    for p in before:p.write_bytes((out/('after-'+p.name)).read_bytes())
    result=dict(root=str(out),proposal_sha256=sha(out/'proposal.json'),report_sha256=sha(out/'proposal.md'),seal_sha256=sha(out/'seal.json'),
        source_condition_pending=True,launch_ready=False)
    save(HERE/'proposal-published.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
