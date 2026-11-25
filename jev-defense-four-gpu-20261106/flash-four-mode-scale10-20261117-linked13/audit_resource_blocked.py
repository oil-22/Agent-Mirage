"""Audit three consecutive resource blockers without inventing new progress."""
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, save, sha
from join_reviewed_results import verify
from reserve_cumulative_accounting import counts_from_rows


def read_binding(binding, filename):
    root=verify(binding['root'],binding['seal_sha256'])
    return json.loads((root/filename).read_bytes())


def main():
    assert not(HERE/'blocked-audit-current.json').exists()
    prepared=json.loads((HERE/'prepared-publication-current.json').read_bytes())
    read_binding(prepared,'publication.json')
    compatible=json.loads((HERE/'reserve-readiness-publication-current.json').read_bytes())
    read_binding(compatible,'publication.json')
    latest=json.loads((HERE/'resource-admission-current.json').read_bytes())
    observations=[
        {'turn':'original26_preparation_turn','classification':'progress: exact26 prepared, qualified and staged',
         'binding':prepared['resource_binding']},
        {'turn':'future_reserve_compatibility_turn','classification':'progress: required reserve path and ancestor compatibility qualified',
         'binding':compatible['resource_binding']},
        {'turn':'current_blocked_audit_turn','classification':'no experimental progress: same external resource blocker',
         'binding':latest}]
    assert len({r['binding']['root']for r in observations})==3
    times=[]
    for row in observations:
        value=read_binding(row['binding'],'result.json')['result']
        assert value['state']=='waiting_exclusive_eight_GPUs'
        assert value['eligible_for_first_submission'] is False and value['new_GPU_lease'] is False
        assert value['new_model_GUI_calls']==0
        snapshot=value['snapshot'];compute=snapshot['compute']
        assert compute and all(r['identity']['uid']==1006 for r in compute)
        occupied={i for i,card in snapshot['gpu'].items()if any(r['uuid']==card['uuid']for r in compute)}
        empty={i for i,card in snapshot['gpu'].items()if card['free_mib']>=23000 and not any(r['uuid']==card['uuid']for r in compute)}
        assert occupied=={'0','1','2','3'}and empty=={'4','5','6','7'}
        assert len(value['kernel_locks'])==17 and not any(r['kernel_locks']for r in value['kernel_locks'])
        row.update(time=value['time'],foreign_UIDs=[1006],occupied_GPUs=sorted(occupied),empty_GPUs=sorted(empty))
        times.append(value['time'])
    assert times[0]<times[1]<times[2]
    assert compatible['useful_operational_preparation_remaining'] is False
    prep=json.loads((HERE/'preparation-current.json').read_bytes())
    verify(prep['root'],prep['seal_sha256']);m=manifest()
    assert sha(PACKAGE/'manifest.json')==prep['manifest_sha256']==prepared['manifest_sha256']==compatible['manifest_sha256']
    for name,digest in m['files'].items():assert sha(PACKAGE/name)==digest,name
    qualification=json.loads((HERE/'CPU-routing-current.json').read_bytes())
    assert qualification['passed'] and qualification['manifest_sha256']==prep['manifest_sha256']
    read_binding(qualification,'result.json')
    auditors=json.loads((HERE/'audit-preparation-current.json').read_bytes())
    for name,digest in read_binding(auditors,'result.json')['files'].items():assert sha(HERE/name)==digest,name
    for host in['3090','4090']:
        staged=json.loads((HERE/('stage-'+host+'.json')).read_bytes())
        assert staged['result']['manifest_sha256']==prep['manifest_sha256']
    future=json.loads((HERE/'future-reserve-preparer-current.json').read_bytes())
    qualified=read_binding(future,'result.json')
    assert qualified['actual_reserve_plan_or_campaign_created'] is False
    assert qualified['cannot_use_until_original26_completed_audited_released_and_reported']
    assert sha(future['preparer_path'])==future['preparer_sha256']
    parent=m['unstarted_parent_binding'];report=read_binding(parent,'report.json')
    counts=counts_from_rows(report['cumulative_rows'])
    assert counts==dict(silent_drop=4,blank_replace=4,stale_replace=3,buttons_only=3)
    assert len(report['cumulative_rows'])==24 and len(report['rows'])==14
    assert m['remaining_queue']==read_binding(parent,'unstarted-plan.json')['exact_unstarted_queue']
    assert len(m['remaining_queue'])==26
    assert not({r['run_id']for r in m['remaining_queue']}&{r['run_id']for r in report['rows']})
    for name in['service-submission.json','GUI-submission.json','reserve-child-intent.json']:
        assert not(HERE/name).exists(),name
    absence=sorted(HERE.glob('blocked-audit-GUI-absence-*'))[-1]
    verify(absence)
    gui_absence=json.loads((absence/'result.json').read_bytes())['result']
    assert gui_absence['new_GUI_not_started'] and not gui_absence['matching_actual_processes']
    assert not any(gui_absence['paths'].values())
    requirements=[
        {'requirement':'each of four injections >=10 verified complete GUI recovery trajectories',
         'state':'incomplete','actual_counts':counts,'deficits':{k:10-v for k,v in counts.items()},'evidence':parent},
        {'requirement':'retain all prior terminals/failures/untriggered/infrastructure and exact unstarted order',
         'state':'verified for existing24 rows and staged26','evidence':parent},
        {'requirement':'same single-image Flash, full primary history, BF16/native parser/action/budgets',
         'state':'source identity/CPU qualification verified for staged26; actual new inference unstarted',
         'evidence':qualification},
        {'requirement':'all8 GPUs empty with headroom and fresh inherited owned locks before launch',
         'state':'blocked by foreign UID1006 onGPU0-3 across3 consecutive goal turns','evidence':observations},
        {'requirement':'run exact remaining26 before any reserve and review all actual raw/image/normal-control evidence',
         'state':'incomplete; no new model/GUI launch; cannot audit nonexistent calls','evidence':prep},
        {'requirement':'deficient-mode reserves in original frozen order, once-only and new package qualified',
         'state':'gated preparer qualified; forbidden before current26 finishes','evidence':future},
        {'requirement':'all future results/cost/resource releases and full final goal audit',
         'state':'incomplete; requires actual experiments, not preparation receipts'}]
    root=HERE/('resource-blocked-audit-'+str(time.time_ns()));root.mkdir()
    save(root/'audit.json',{'blocked_audit_passed':True,'same_blocking_condition_across_consecutive_goal_turns':3,
        'observations':observations,'requirements':requirements,
        'manifest_sha256':prep['manifest_sha256'],'existing_successes':counts,
        'new_model_GUI_calls':0,'new_successes':0,
        'existing_no_completion_claim':True,'original_full_objective_unchanged':True,
        'no_experimental_process_confirmed_live_for_verified_wait':True,
        'why_no_further_safe_progress':['current and required future operational preparation finished',
            'running primary requires all8 free with owned locks; foreign compute cannot be preempted/shared',
            'reserve prepare is intentionally blocked until actual26 terminal audit/release/report',
            'rerunning old terminals or changing history/precision/placement/budget violates this protocol',
            'further status copies or repeated completed CPU controls would not advance the requested experiments'],
        'external_change_required':'3090 all8 empty/free>=23000MiB with no unverified compute and fresh17 inherited task locks',
        'fresh_resume_must_revalidate_resources_and_existing_launch_receipts':True,
        'current_GPU_model_GUI_allocation_zero':True,
        'GUI_absence_binding':{'root':str(absence),'seal_sha256':sha(absence/'seal.json')},
        'prepared_binding':{'root':prepared['root'],'seal_sha256':prepared['seal_sha256']},
        'reserve_compatibility_publication':{'root':compatible['root'],'seal_sha256':compatible['seal_sha256']}})
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    verify(root)
    binding={'root':str(root),'seal_sha256':sha(root/'seal.json')}
    save(HERE/'blocked-audit-current.json',binding)
    print(json.dumps({**binding,'blocked_audit_passed':True,'three_consecutive_goal_turns_same_resource_blocker':True,
        'safe_independent_preparation_remaining':False,'existing_successes':counts,'goal_tool_update_still_required':True}))


if __name__=='__main__':main()
