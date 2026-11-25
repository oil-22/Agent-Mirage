"""CPU-only exact-suffix plan validation; no network, model or launch capability."""
import copy,hashlib,json

ORIGINAL_PLAN_SHA='a6e248f730408ab9c5bbaeb72bfa0d392ecf99f247159495273d2b3f5616ef8e'
ORIGINAL_STATE_SHA='967bf98cbb5230a0a87d8151903ea725b8fc355ce3ca7ffda881468d62d26ae9'
EXPECTED=[('clean',True),('stale_replace',False),('stale_replace',True)]

def require(value,message):
    if not value:raise ValueError(message)

def parent_plan(raw):
    require(hashlib.sha256(raw).hexdigest()==ORIGINAL_PLAN_SHA,'Original immutable plan identity differs')
    plan=json.loads(raw);q=plan['queue']
    require(len(q)==4 and [(r['condition'],r['observer_enabled'])for r in q]==
        [('clean',False)]+EXPECTED,'Original reviewed order differs')
    require(len({r['run_id']for r in q})==4,'Duplicate parent run IDs')
    return plan

def validate_parent_state(state,original):
    q=original['queue'];require(state['phase']=='terminal_failure'and state['active']is None and
        type(state['next_run_index'])is int and state['next_run_index']==1,'Original group is not exact terminal first-run failure')
    require(set(state['runs'])=={r['run_id']for r in q},'Original source run inventory differs')
    first=state['runs'][q[0]['run_id']]
    require(first=={'status':'technical_failure','last_decision_index':15,
        'calls':{'actor':16,'judge':57,'observe':0}},'Completed/failed baseline may not be reset or hidden')
    for row in q[1:]:
        require(state['runs'][row['run_id']]=={'status':'not_started','last_decision_index':0,
            'calls':{'actor':0,'judge':0,'observe':0}},'A migrated trajectory already began or spent a call')

def prepare_plan(original_raw,state):
    original=parent_plan(original_raw);validate_parent_state(state,original)
    proposed=copy.deepcopy(original);proposed['queue']=copy.deepcopy(original['queue'][1:])
    proposed['stage']='source_CPU_preparation_launch_not_ready'
    validate_plan(proposed,original)
    return proposed

def validate_plan(proposed,original):
    expected=copy.deepcopy(original);expected['queue']=copy.deepcopy(original['queue'][1:])
    expected['stage']='source_CPU_preparation_launch_not_ready'
    require(proposed==expected,'Only the exact untouched unstarted suffix and stage may differ')
    q=proposed['queue'];require([(r['condition'],r['observer_enabled'])for r in q]==EXPECTED,'Exact three-run migration order differs')
    require(type(proposed['max_steps'])is int and proposed['max_steps']==50,'Step cap differs')
    require(proposed['limits']=={'max_recaptures_per_decision':2,'max_regenerations_per_decision':2,
        'max_actor_calls':70,'max_verifier_calls':140,'wait_seconds':[0.5,1.0]},'Recovery or call budgets differ')
    require(proposed['actor_output_tokens']==2048 and proposed['verifier_output_tokens']==4096 and
        proposed['max_format_retries']==1 and proposed['auxiliary_calls_per_trajectory']==60,'Output/retry/observer caps differ')
    return {'trajectories':3,'maximum_primary_calls':630,'maximum_observer_calls':120,
        'old_baseline_reexecuted':False,'launch_ready':False,'actual_GPU_GUI_or_model_calls':0}
