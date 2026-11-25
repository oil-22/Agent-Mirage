"""Record the returned goal blocked state; never launch or change resources."""
import json
import time
from pathlib import Path

from control import HERE, save, sha
from join_reviewed_results import verify


def main():
    tool_path=HERE/'goal-blocked-tool-result.json'
    returned=json.loads(tool_path.read_bytes())
    assert returned['goal']['status']=='blocked'
    assert returned['goal']['threadId']=='01a151bb-be3f-74c2-982d-a004f4a51038'
    assert not(HERE/'blocked-publication-current.json').exists()
    audit_binding=json.loads((HERE/'blocked-audit-current.json').read_bytes())
    audit_root=verify(audit_binding['root'],audit_binding['seal_sha256'])
    audit=json.loads((audit_root/'audit.json').read_bytes())
    assert audit['blocked_audit_passed']and audit['same_blocking_condition_across_consecutive_goal_turns']==3
    previous=json.loads((HERE/'continuation-current.json').read_bytes())
    verify(previous['root'],previous['seal_sha256'])
    root=HERE/('blocked-goal-publication-'+str(time.time_ns()));root.mkdir()
    before=root/'before';before.mkdir()
    parent=HERE.parent/'flash-four-mode-scale10-20261116-12'
    heads=[HERE/'README.md',HERE/'HANDOFF.md',HERE/'REVIEW_HANDOFF.md',
        HERE.parent/'README.md',HERE.parent/'HANDOFF.md',
        parent/'README.md',parent/'HANDOFF.md',parent/'REVIEW_HANDOFF.md']
    active=HERE.parent/'active-defense-goal-current.json'
    for i,path in enumerate([*heads,active]):
        if path.exists():(before/(str(i)+'-'+path.name)).write_bytes(path.read_bytes())
    value={key:val for key,val in previous.items()if key not in['root','seal_sha256']}
    value.update(state='goal_blocked_external_exclusive_eight_GPU_resources',goal_status='blocked',
        goal_active=False,goal_work_complete=False,original_objective_unchanged=True,
        previous_publication_binding={'root':previous['root'],'seal_sha256':previous['seal_sha256']},
        blocked_audit_binding=audit_binding,resource_binding=audit['observations'][-1]['binding'],
        goal_tool_returned_status='blocked',goal_tool_return_sha256=sha(tool_path),
        current_goal_turn_classification='no experimental progress;3-turn same resource blocker audit passed',
        monitor_or_automation_changes_made=False,new_model_GUI_calls=0,new_verified_successes=0,
        useful_operational_preparation_remaining=False)
    value['next_actions']=[
        'External change required: original3090 eight empty task-allocatable GPUs, each>=23000MiB and no foreign compute; do not preempt/share or alter the protocol.',
        'On user resumption of the blocked goal, start a fresh blocked audit and run inspect_admission_wait.py; never rely on this old resource snapshot or a PID.',
        'If no existing launch receipt and fresh admission passes, control.py submit once (never stage again); verify actual readiness/UID/fullcmd/start/17 inherited owned locks, then gui once/site-lock audit and a fresh single foreground watcher.',
        'Complete exact26 original unstarted rows with full raw/image/normal-control audits, group terminal/release/cost and report, then original frozen reserves via qualified prepare_reserve_after_current.py until every mode>=10.',
        'All prior24 rows and current4/4/3/3 counts remain immutable; all attempted failures/untriggered/infrastructure preserved; no overall Mirage rate or Flash freshness claim.'
    ]
    save(root/'publication.json',value)
    (root/'goal-tool-result.json').write_bytes(tool_path.read_bytes())
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
    verify(root)
    pointer={'root':str(root),'seal_sha256':sha(root/'seal.json'),**value}
    save(HERE/'blocked-publication-current.json',pointer)
    for path in[active,HERE/'continuation-current.json',parent/'unstarted-continuation-current.json']:
        tmp=path.parent/('.blocked-goal-'+str(time.time_ns()));save(tmp,pointer);tmp.replace(path)
    header=f'''## 2026-11-17 目标已按三轮资源阻塞审计标blocked；原26待资源，完整目标未完成

目标工具实际返回 `blocked`（不是complete或用户暂停）。权威 `{root / 'publication.json'}`，blocked-audit-current.json 三轮实际回执均证明：3090 GPU0-3仍实际UID1006外部compute，仅4-7空且24253MiB；当前7主＋1Flash方案不能取得8卡独占租约。17资源内核锁无占用；新主/Flash未提交，4090实际新GUI目录/进程均不存在。前两轮完成必要准备，本轮已无安全独立推进动作；进一步实验需外部资源状态变化。不抢占/共享外人，不缩短历史/改精度或重跑旧终局。

当前有效目录 `{HERE}`，stage manifest151c5bab54d631d9d8da2af898e270ee53d0f62dde5caf7c587d0f8647e400b8不变。原26未开队列、CPU资格、两端stage、新父中断绑定和后续备用预备器均已备妥；不要再stage。累计缺图/白图/旧帧/按钮完整成功4/4/3/3，缺口6/6/7/7，全部24旧终局保留，0新增调用/成功。

资源满足后用户恢复目标，先开始新的blocked audit并inspect_admission_wait.py复核实际UID/fullcmd/UUID/headroom/locks和有无launch回执；仅无既有launch且原8卡条件满足才submit一次，实际ready与17继承锁后gui一次、新站点锁审计、新前台watcher。旧exec1198已终局，不得poll/重开。原26全终局/全raw与原图审查/正常对照/成本/释放/报告后才用已资格prepare_reserve_after_current.py按原备用顺序补缺，直至每种>=10且最终审计完成。未改任何automation或其他监控状态。以下旧ACTIVE快照仅作历史。

'''
    for i,path in enumerate(heads):
        prior=before/(str(i)+'-'+path.name)
        path.write_text(header+(prior.read_text('utf8')if prior.exists()else''),encoding='utf8')
    print(json.dumps({'root':str(root),'goal_status':'blocked','original_goal_complete':False,
        'counts':audit['existing_successes'],'new_model_GUI_calls':0,'all_current_queues_evidence_preserved':True}))


if __name__=='__main__':main()
