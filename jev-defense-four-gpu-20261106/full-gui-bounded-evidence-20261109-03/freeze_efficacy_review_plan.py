"""Freeze assessment definitions before new GUI outcomes are known."""
import json
import time
from remote_control import HERE,BASE,save,sha

out=HERE/'assessment-plan-01';out.mkdir(exist_ok=False)
plan={'time':time.time(),'condition_manifest_sha256':sha(HERE/'runtime-package/manifest.json'),
    'scope':'One already-known task, four finite clean/stale_replace x auxiliary-disabled/enabled development tracks',
    'primary_endpoint':'Trajectory contains any definite boundary-inclusive semantic Mirage; count occurrence even if rejected, unexecuted or later corrected; pure native WAIT excluded',
    'secondary_axes':['candidate definite positives and unresolved subclaims','accepted positives','accepted and executed positives',
        'native direction/target errors, distinct from semantic Mirage','recovery, never erases prior occurrence',
        'correct native operation false blocks','official task score and completed/executed steps','technical failures and output caps','auxiliary contract availability and wrong evidence'],
    'comparison':'Within clean and stale conditions, auxiliary enabled vs disabled; same latest main checks, full inputs and original per-track budgets',
    'matched_task_not_independent_replication':True,
    'review_method':'Source image, full lawful history and candidate first; seal semantic labels before joining private actual execution and scorer when feasible. Reviewer may recognize the known task. Record deviations from outcome blinding.',
    'false_block_definition':'Proposed native action is supported by readable actual supplied pixels/source and allowed by the native contract, but blocked on false evidence; retain unclear cases as unresolved',
    'normal_operation_requirement':'A lower count explained by premature stop, fewer opportunities, technical failure, or task-completion deterioration cannot establish efficacy',
    'zero_baseline':'Report absolute difference; relative reduction undefined when denominator is zero',
    'development_target_relative_reduction':0.30,'aspiration':0.50,
    'general_efficacy':'Requires source-bound disjoint tasks and an independently frozen matched evaluation; this known-task batch alone cannot establish a general reduction or statistical significance',
    'cost':'Separate actual per-model requests/tokens/call durations from instrumentation, full GUI walltime, loading and all four reserved GPU-seconds. No currency/energy or savings invented.',
    'do_not_pool':['Prior mixed revisions','Completed failed controls','technical failures as model zeros','CPU preflight as generation','format valid as semantic pass','task official1 as no Mirage'],
    'all_failures_and_raw_sources_retained':True,'old_terminal_retries_or_automatic_budget_expansion':False,
    'goal_remains_active_until_evidence':True}
save(out/'plan.json',plan);save(out/'seal.json',{'plan.json':sha(out/'plan.json')})
print(json.dumps({'assessment_plan_frozen':str(out),'known_task_not_general_efficacy':True}))
