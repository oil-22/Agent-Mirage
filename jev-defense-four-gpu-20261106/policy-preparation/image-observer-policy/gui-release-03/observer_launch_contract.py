"""New image-only/direct-actor GUI condition gate; no legacy readiness bypass."""
import hashlib,json
from pathlib import Path
from image_observer import POLICY,MODEL,REVISION,wire,contract,SHARED_ACTOR_INSTRUCTIONS


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(ready,key):
    item=ready['evidence'][key]
    path=Path(item['path'])
    if sha(path)!=item['sha256']:raise RuntimeError('Evidence changed: '+key)
    return json.loads(path.read_bytes())


def validate_launch_inputs(args):
    r=json.loads(args.readiness.read_bytes())
    if r.get('policy')!=POLICY or r.get('launch_ready')is not True:
        raise RuntimeError('New observer GUI prerequisites incomplete; no model or GUI access')
    p=json.loads(args.plan.read_bytes())
    if r['plan_sha256']!=sha(args.plan)or p['policy']!=POLICY:raise RuntimeError('Plan identity differs')
    if p['limits']!={'max_recaptures_per_decision':2,'max_regenerations_per_decision':2,
       'max_actor_calls':70,'max_verifier_calls':140,'wait_seconds':[0.5,1.0]}:raise RuntimeError('Original main budgets changed')
    fixed={'max_steps':50,'actor_output_tokens':2048,'verifier_output_tokens':4096,
       'max_format_retries':1,'auxiliary_calls_per_trajectory':60,'seed':20261011}
    if any(type(p[k])is not int or p[k]!=v for k,v in fixed.items()):raise RuntimeError('Original condition changed')
    q=p['queue']
    if len(q)!=4 or len({x['run_id']for x in q})!=4 or any(x['dataset']!='vwa'or x['arm']!='joint'or type(x['observer_enabled'])is not bool for x in q):
        raise RuntimeError('Unreviewed expanded queue')
    if {(x['observer_enabled'],x['condition'])for x in q}!={(False,'clean'),(True,'clean'),(False,'stale_replace'),(True,'stale_replace')}:
        raise RuntimeError('Matched observer/no-observer conditions required')
    if p['shared_actor_instructions_sha256']!=hashlib.sha256(SHARED_ACTOR_INSTRUCTIONS.encode()).hexdigest()or p['observer_native_contract_sha256']!=hashlib.sha256(wire(contract())).hexdigest():
        raise RuntimeError('Frozen shared actor boundary or image-only contract changed')
    private=json.loads(args.native_task.read_bytes())
    if sha(args.native_task)!='b2dd3cef7cc6357376b95ef8c64ae4fcad839fd7f705e55afbdeb4a3d6a83603'or p['tasks']['vwa']!=[{'pilot_task_id':'classifieds_112','image':None,'intent':private['intent']}]:
        raise RuntimeError('Original task or intent changed')
    if sha(args.actor_template)!='b2a0af4ba02e3316cb060cddc2e0a1b20d6e00eabce04358387f5e8f46278add'or sha(args.runtime/'native/run_reddit_internvl_smoke.py')!='af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7':
        raise RuntimeError('Original native actor/parser artifact changed')
    c=json.loads(args.auxiliary_config.read_bytes())
    if c.get('policy')!=POLICY or c.get('model')!=MODEL or c.get('revision')!=REVISION or c.get('max_auxiliary_calls')!=60 or c.get('deployment_applied')is not True:
        raise RuntimeError('Single fixed observer configuration not applied')
    checks={
      'observer_independent_review':['actual_input_forward_audited','original_source_images_reviewed','passed_for_gui_development','no_defense_success_claim'],
      'primary_full_input_capacity':['capacity_passed','full_input_preserved','actual_input_forward_audited','output_budget_4096_preserved'],
      'actor_observer_policy_cpu':['tests_passed','source_binding_negative_passed','shared_instructions_equal','original_judge_unchanged'],
      'same_live_environment':['same_live_recapture_passed','native_parser_passed','official_scorer_transport_passed','no_site_reset'],
      'ownership_transport':['actual_uid_full_command_verified','all_inherited_locks_held','no_foreign_compute_on_leased_GPUs','transport_ready','outer_launcher_rechecks_fresh'],
      'user_condition':['image_only_direct_actor_authorized','single_fixed_observer_authorized','four_gpu_new_layout_authorized'],
      'terminal_auditor':['ready','actual_wire_request_reply_audit','event_chain_and_terminal_seal_audit','no_duplicate_launch']}
    for key,fields in checks.items():
        obj=evidence(r,key)
        if any(obj.get(k)is not True for k in fields):raise RuntimeError('Missing concrete prerequisite: '+key)
    terminal=evidence(r,'observer_terminal')
    cap=terminal.get('max_new_flash_calls')
    if type(cap)is not int or not 1<=cap<=60 or terminal.get('terminal')is not True or terminal.get('status')!='completed'or terminal.get('complete_replies')!=cap or terminal.get('error'):
        raise RuntimeError('New neutral observer finite preflight incomplete')
    prompt=evidence(r,'current_prompt_disclosure')
    if prompt.get('current_exact_texts_and_hashes_frozen')is not True or prompt.get('historical_binding_not_claimed')is not True:
        raise RuntimeError('Current prompt condition disclosure missing')
    release=Path(__file__).resolve().parent
    for name,expected in r['release_sha256'].items():
        path=(release/name).resolve()
        if not path.is_relative_to(release)or sha(path)!=expected:raise RuntimeError('Runtime release source changed')
    mandatory=['image_observer.py','observer_launch_contract.py','run_image_observer_vwa_validation.py','online_transport.py','defense/core.py','defense/prompts.py']
    if any(k not in r['release_sha256']for k in mandatory):raise RuntimeError('Actual active source files not bound')
