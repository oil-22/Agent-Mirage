"""New28 continuation and denial-boundary CPU checks, no model/browser imports."""
import builtins
import copy
import importlib
import json
from pathlib import Path
import runpy
import sys

package,old,proposed=map(lambda v:Path(v).resolve(),sys.argv[1:])
sys.path.insert(0,str(package))
continuation=importlib.import_module('continuation_manifest')
protocol=importlib.import_module('protocol')
gate=importlib.import_module('source_decision_gate')


def read(path):
    return json.loads(path.read_bytes())


def refused(call):
    try:call()
    except(AssertionError,gate.PendingSourceDecision):return
    raise AssertionError('Expected boundary refusal')


def main():
    groups=[]
    def check(label,value):
        assert value,label
        groups.append(label)
    plan=read(package/'plan.json');source=read(package/'continuation.json')
    queue=continuation.remaining_queue(plan);ids=continuation.completed_request_ids()
    check('original_full32_plan_exact_bytes_8tasks_16pairs', (package/'plan.json').read_bytes()==(old/'plan.json').read_bytes()and len(plan['queue'])==32 and len({r['task_id']for r in plan['queue']})==8 and len({(r['task_id'],r['condition'])for r in plan['queue']})==16)
    check('all_four_completed_tracks_excluded_original_order28',queue==plan['queue'][4:]and source['excluded_run_ids']==[r['run_id']for r in plan['queue'][:4]])
    check('remaining14_pairs_each_has_both_arms',len({(r['task_id'],r['condition'])for r in queue})==14 and all(len([r for r in queue if(r['task_id'],r['condition'])==pair])==2 for pair in{(r['task_id'],r['condition'])for r in queue}))
    check('first_new_task3_stale_noaux',queue[0]['run_id']=='fullhistory23-T003-stale_replace-noaux')
    check('437_completed_model_request_ids_source_bound',len(ids)==437)
    carry=read(package/'carryover/state.json')
    counter=0
    def ident():
        nonlocal counter
        counter+=1;value=format(counter,'032x');assert value not in ids;return value
    def begin(b,**kw):
        row=dict(trajectory_id=b.queue[b.index]['run_id'],request_id=ident());row.update(kw);return b.admit('/begin',row)
    def call(b,op,**kw):
        row=dict(trajectory_id=b.active,decision_index=1,attempt_index=b.counts[op]+1,request_id=ident(),payload=dict(operation=op));row.update(kw)
        return b.admit('/evidence'if op=='evidence'else'/',row)
    b=protocol.RunBudget(plan,carry)
    for value in ids:refused(lambda value=value:begin(b,request_id=value))
    for value in source['excluded_run_ids']:refused(lambda value=value:begin(b,trajectory_id=value))
    check('every_old_request_and_track_refused_before_begin',b.active is None and b.index==0)
    for row in queue:
        begin(b);assert b.counts==dict(actor=0,judge=0,evidence=0)
        if row['observer_enabled']:call(b,'evidence')
        else:refused(lambda:call(b,'evidence'))
        call(b,'actor');call(b,'judge')
        b.admit('/end',dict(trajectory_id=b.active,request_id=ident(),status='completed',terminal_receipt_sha256='e'*64))
    check('synthetic28_begin_zero_original_order_and_finite_end_not_real_GUI',b.terminal and len(b.done)==28 and not b.failed)
    for op,cap in [('actor',70),('judge',140),('evidence',60)]:
        b=protocol.RunBudget(plan,carry)
        if op=='evidence':
            begin(b);b.admit('/end',dict(trajectory_id=b.active,request_id=ident(),status='completed',terminal_receipt_sha256='e'*64))
        begin(b)
        for _ in range(cap):call(b,op)
        refused(lambda:call(b,op));assert b.counts[op]==cap
    check('original70actor140judge60aux_caps_enforced',True)
    for end in ['technical_failure','stopped']:
        b=protocol.RunBudget(plan,carry);begin(b)
        b.admit('/end',dict(trajectory_id=b.active,request_id=ident(),status=end,terminal_receipt_sha256='e'*64))
        refused(lambda:begin(b));assert b.failed and b.terminal
    check('new_terminal_never_auto_retried',True)
    changed=copy.deepcopy(plan);changed['limits']['max_verifier_calls']+=1
    refused(lambda:continuation.remaining_queue(changed))
    check('budget_changes_rejected',True)
    real_import=builtins.__import__;blocked={'torch','transformers','PIL','playwright','fcntl','socket','subprocess'}
    def guarded(name,*args,**kwargs):
        assert name.split('.')[0]not in blocked,'Entry imported execution dependency before decision: '+name
        return real_import(name,*args,**kwargs)
    for entry in ['gpu_server.py','launch_gui_service_once.py','gui_outer.py','run_independent_gui.py']:
        builtins.__import__=guarded
        try:refused(lambda entry=entry:runpy.run_path(str(package/entry),run_name='__main__'))
        finally:builtins.__import__=real_import
    check('all_four_entrypoints_refuse_before_execution_imports',True)
    old_manifest=read(old/'manifest.json')
    changed_nonrelease={'admission.json','source_decision_gate.py','continuation_manifest.py','continuation.json',
        'completed-request-exclusions.json','gpu_server.py','launch_gui_service_once.py','primary-reference.json','preflight_support.py'}
    for name in old_manifest['files']:
        if name.startswith('release/'):
            assert (package/name).read_bytes()==(proposed/name.removeprefix('release/')).read_bytes(),name
        elif name not in changed_nonrelease:
            assert (package/name).read_bytes()==(old/name).read_bytes(),name
    check('exact_prepared_release_all_other_runtime_aux_history_protocol_sources_unchanged',True)
    manifest=read(package/'manifest.json')
    check('template_not_authorized_or_ready',manifest['template_only']and not manifest['launch_ready']and not manifest['authorized_finite_joint_development']and not read(package/'admission.json')['admit_new_GUI_development'])
    # Old STOP approval exists only as provenance; it cannot authorize the new wire condition.
    check('prior_STOP_source_approval_retained_but_not_reused',(package/'human-source-condition-decision.json').exists()and not(package/'human-source-reference-condition-decision.json').exists())
    for name,expected in manifest['files'].items():assert continuation._sha(package/name)==expected,name
    check('all_template_file_hashes_verified',True)
    print(json.dumps(dict(passed=True,groups=groups,group_count=len(groups),new_model_GPU_GUI_scorer_paid_calls=0,
        synthetic_protocol_controls_not_experimental_tracks=True,real_semantic_negative_WAIT_capacity_controls_not_run=True)))


if __name__=='__main__':main()
