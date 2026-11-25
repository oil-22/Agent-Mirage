"""Publish CPU-only execution readiness and the still-pending human decision."""
import hashlib
import json
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
PREP=HERE.parent
PARENT=PREP.parent
BASE=PARENT.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8',newline='\n')as f:
        json.dump(value,f,ensure_ascii=False,indent=2)


def verify(pointer):
    value=json.loads(pointer.read_bytes());root=Path(value['root'])
    assert sha(root/'seal.json')==value['seal_sha256']
    for name,h in json.loads((root/'seal.json').read_bytes()).items():
        assert sha(root/name)==h,name
    return root


def main():
    assert not(PREP/'execution-preparation-current.json').exists()
    checks=verify(HERE/'CPU-checks-current.json')
    stage=verify(HERE/'CPU-stage-linked03-current.json')
    generations=verify(HERE/'generation-bindings-current.json')
    proposal=json.loads((PREP/'publication-current.json').read_bytes())
    publication=Path(proposal['publication'])
    assert sha(publication/'seal.json')==proposal['seal_sha256']
    assert not proposal['new_condition_authorized']
    assert json.loads((checks/'result.json').read_bytes())['passed']==68
    staged=json.loads((stage/'result.json').read_bytes())
    assert staged['result']['passed']==8 and staged['result']['model_GPU_GUI_Flash_scorer_calls']==0
    package=HERE/'package-linked03';manifest=json.loads((package/'execution-manifest.json').read_bytes())
    assert sha(package/'execution-manifest.json')==staged['result']['manifest_sha256']
    assert manifest['proposal_seal_sha256']==proposal['seal_sha256']
    for name,h in manifest['files'].items():
        assert sha(package/name)==h,name
    assert (package/'offline_protocol.py').read_bytes()==(checks/'offline_protocol.py').read_bytes()
    assert not(package/'authorization.json').exists()
    assert len(manifest['cases'])==10
    root=HERE/('execution-publication-'+str(time.time_ns()));root.mkdir()
    for name in ['build_package.py','build_package_linked02.py','build_package_linked03.py',
                 'stage_cpu_only.py','stage_cpu_only_linked03.py','publish_execution_preparation.py']:
        (root/name).write_bytes((HERE/name).read_bytes())
    save(root/'status.json',{
        'time':time.time(),'goal':'active','previous_goal_turn_classification':'progress',
        'current_goal_turn_classification':'progress','current_state':'waiting_user_decision',
        'pending_question_already_sent_no_duplicate_question':True,
        'same_pending_decision_consecutive_goal_turns_including_original':2,
        'no_permission_inferred_from_automatic_goal_continuation':True,
        'condition':'same-primary-history-image-preread-v1','proposal':proposal,
        'new_calls_cap_pending_approval':20,'formal_new_GUI_authorized':False,
        'package':str(package),'package_manifest_sha256':sha(package/'execution-manifest.json'),
        'remote_package':manifest['remote_package'],'planned_output':manifest['output'],
        'study_claim_root':manifest['study_claim_root'],
        'CPU_protocol_checks':str(checks),'CPU_protocol_seal_sha256':sha(checks/'seal.json'),
        'CPU_mocked_protocol_checks':68,'actual_Linux_import_scope_denial_checks':8,
        'repeated_eight_checks_in_older_source_stage_not_added_as_new_independent_checks':True,
        'Linux_CPU_stage':str(stage),'Linux_CPU_stage_seal_sha256':sha(stage/'seal.json'),
        'original_effective_generation_bindings':str(generations),
        'original_effective_generation_bindings_seal_sha256':sha(generations/'seal.json'),
        'generation_binding_cases':10,'distinct_original_effective_configs':1,
        'unchanged_native_source_files':44,
        'original_backend_sha256':sha(package/'native/release/defense/qwen_backend.py'),
        'actual_authorization_or_GPU_lease_created':False,'actual_model_GPU_GUI_Flash_scorer_calls':0,
        'model_import_loading_and_first_forward_NOT_TESTED':True,
        'new_native_recorder_real_numerical_equivalence_or_capacity_NOT_TESTED':True,
        'real_WAIT_or_NO_recapture_semantics_NOT_TESTED':True,
        'formal_GUI_release':False,'effectiveness_proven':False,
        'actual_actor_dynamic_inputs_still_require_real_reading_then_native_CPU_and_first_forward_checks':True,
        'all_old_trials_and_completed_audits_unchanged_not_repeated':True})
    report='''# 历史原图预读执行准备：等待已提出的20次开发调用决定

本轮完成了隔离执行包和CPU准入检查，新增模型/GPU/GUI/Flash/评分调用均为0。上一轮提问中的条件、提示、10个来源和最多20次预算不变；真实批准文件尚未创建，没有提交任何推理命令，也没有取得新的GPU锁。

68项CPU执行检查用真实冻结输入和明确的假回调，验证缺失批准/旧十次授权/预算扩大被拒、20次固定顺序与上限、同一授权不能换attempt重跑、无效预读跳过对应actor、技术失败不重试，以及晚到资源冲突保留已返回原文和完整事件SHA链。它们不是模型推理、真实WAIT、GPU容量或语义通过。

隔离源包在原Linux环境另通过8项CPU检查，包含44份不变原生依赖导入、十条完整来源/CPU包装→原结果绑定，以及缺失批准、旧范围和CPU伪批准在加载前被拒。没有导入torch、加载模型或创建真实授权。早期静态包少列原生four_gpu_contract依赖，已保留旧包，在关联源包补齐；最终源包另保留原actor每次调用后的allocator空缓存行为，并记录原设备累计内存峰值。旧源包和旧CPU回执均保留，不把重复的8项检查加成新独立样本。

十份原始effective-generation文件均与各自原request seal绑定，默认配置相同。原LocalQwen生成后端逐字节保留（SHA见status）；新记录外层对预读显式使用4096，actor2048，其余有效配置逐字段匹配原记录。原actor外层固定2048，未把它冒称可直接执行4096预读，也未声称新的外层经过真实多卡/完整logit验证。

执行时仅原任务和全部原图进入预读；actor完整原system、历史和图片保留，追加原样可能错误的读数。每次真实反馈出现后先将动态actor完整body和原生CPU张量封存，再与实际首次forward核对。没有真实回复前无法证明其动态容量或语义正确。预读JSON合法仅是来源/结构检查，不是视觉真值。

GPU外层保留原UID、完整command/start、UUID、外人compute、显存、九个原继承锁、八个新增UUID锁及推理互斥锁的核验路径。实际启动仍须重新证明归属和空闲；本次CPU导入不能替代这一步。只保留原BF16七卡主模型布局，实际八卡保留都计入记录。主模型新预读/actor之外不启动Flash服务、旧GUI队列、浏览器或评分器，不自动追加容量生成。

当前唯一待决事项仍是上方已提出的20次离线开发批准。上一轮十次调用已用完，不把自动目标续行当成新授权。正式新GUI没有批准，真实WAIT、NO持续复拍和完整轨迹的有效性仍未验证。降低Mirage尚未证明，总目标保持ACTIVE。

所有源码、CPU回执、原生成配置和计划SHA的精确路径见status.json；原10条预检/29GUI终局和全部已完成全量审计均未重跑。下一轮若仍没有此决定且无其他有意义的已授权工作，按连续三轮阻塞规则核查后更新目标状态，不用重复静态测试维持表面进展。
'''
    report_path=root/'历史原图预读执行准备与预算保护-20261115.md'
    report_path.write_text(report,encoding='utf8')
    heads=[BASE/'HANDOFF.md',BASE/'README.md',PARENT/'CONTINUATION.md',PARENT/'README.md']
    old=[]
    for i,p in enumerate(heads):
        data=p.read_bytes();old.append((p,data,sha(p)))
        q=root/'previous-heads'/('%02d-'%i+p.name);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
    save(root/'seal.json',{str(p.relative_to(root)).replace('\\','/'):sha(p)for p in root.rglob('*')if p.is_file()})
    pointer={'publication':str(root),'report':str(report_path),'seal_sha256':sha(root/'seal.json'),
             'active_package':str(package),'active_manifest_sha256':sha(package/'execution-manifest.json'),
             'approval_pending':True,'condition_and_original_proposal_unchanged':True,
             'original_proposal_seal_sha256':proposal['seal_sha256'],'new_calls_cap_pending_approval':20,
             'actual_model_GPU_GUI_calls':0,'goal':'active','effectiveness_proven':False}
    save(PREP/'execution-preparation-current.json',pointer)
    save(PARENT/'history-preread-execution-preparation-current.json',pointer)
    header='''## 最新：历史原图预读执行源包已CPU部署检查，20次离线批准仍待答复

权威 history-image-preread-preparation-01/execution-preparation-current.json。仅工程进展，0新模型/GPU/GUI/Flash/scorer。68项CPU假回调执行保护＋8项Linux依赖/来源绑定/未批拒绝检查；派生WAIT非真实语义控制，未导入torch或加载权重/新占GPU。原44原生源/后端/数值内存实现不改，10原effective-generation绑定，预读4096/actor2048其余原配置相同；不称新实际forward/logit/容量通过。

唯一路径 active package-linked03，manifest b971d3ee9c8dcf64a56dc782625773964f598315458a52ef23b1384d23a993bd；旧package/package-linked02及CPU回执保留且无真实授权/调用，绝不提交它们。source-only remote /home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/history-image-preread-development-20261115-01-memory-linked03。未创建授权或command，先等上方已有20次提问，不重问、不把目标自动续行当批准。来源/prompt/预算/原proposal SHA不变，旧10授权已用完，正式GUI未准。

原始完整输入/54图95出现及动态actor输入的CPU/首次forward保护、持久once-only总预算声明/请求claim、晚到外人资源失败后原文保全/事件链均已源实现，仅CPU检查。实际启动须再核UID/fullcmd/start/UUID/compute/显存/继承18锁；原7卡BF16主布局，8卡保留计成本。首次source包缺依赖和后续内存记录/原空缓存行为均留关联版本，不把静态修复当新实测结果。真实WAIT/NO复拍和正式GUI效果仍缺。

上一goal回合progress，本回合progress；相同待批准条件已在含最初提问的2连续goal回合出现。准备已具体到隔离源码和CPU准入；若下一回合仍无真实用户选择且无独立有意义工作，核查后按3轮规则blocked。不要重复旧终局、全量审计或CPU测试凑进展，不暂停/完成目标。目标ACTIVE/降低未证。以下为历史。

'''
    for p,data,expected in old:
        assert sha(p)==expected,'Concurrent handoff update'
        with p.open('w',encoding='utf8',newline='')as f:
            f.write(header+data.decode('utf8'))
    print(json.dumps({'publication':str(root),'report':str(report_path),'approval_pending':True,
                      'actual_model_GPU_GUI_calls':0,'goal':'active'}))


if __name__=='__main__':
    main()
