"""Freeze actual branch lower-bound evidence and an unlaunched recovery copy."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

from orchestrate import COMMON, HERE, OUTPUT, GUIROOT, remote, save, sha
from check_pending_price_budget import run_checks
from pending_price_budget import plan_price_history


def verify(folder):
    for name, expected in json.loads((folder/'seal.json').read_bytes()).items():
        assert sha(folder/name)==expected,str(folder/name)


def main():
    pointer=HERE/'pending-price-recovery-preparation-created.json'
    assert not pointer.exists()
    package=HERE/'runtime-package'
    manifest=json.loads((package/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(package/name)==expected,name
    review_pointer=json.loads((HERE/'source-review-21-created.json').read_bytes())
    review_root=Path(review_pointer['review']);verify(review_root)
    manual=json.loads((review_root/'manual-review-input.json').read_bytes())
    packet_path=HERE/manual['collection']/manual['id']/'packet.json'
    packet=json.loads(packet_path.read_bytes())
    source_pointer=json.loads((HERE/'pagination38-main-source-created.json').read_bytes())
    inputs=Path(source_pointer['root']);verify(inputs)
    payload=json.loads((inputs/'payload.json').read_bytes())
    assert payload['candidate']==packet['candidate']
    image_hashes=[hashlib.sha256(__import__('base64').b64decode(image['raw_base64'])).hexdigest()
                  for image in payload['view']['images']]
    assert len(image_hashes)==len(set(image_hashes))==37
    assert set(image_hashes)=={row['sha256'] for row in manual['original_history_images_actually_viewed']}
    code='ROOT='+repr(GUIROOT)+'\nCANDIDATE_SHA='+repr(packet['candidate_text_sha256'])+'\n'+COMMON+r'''
r=Path(ROOT)
assert os.getuid()==1015
attempt=r/'batch/runs/fullhistory23-T000-clean-noaux/attempt-1794230110024661434'
raw=(attempt/'events.jsonl').read_bytes();lines=raw.splitlines(keepends=True)
partial=bool(lines and not lines[-1].endswith(b'\n'))
if partial:lines.pop()
previous='0'*64;events=[]
for line in lines:
 event=json.loads(line);unsigned=dict(event);signature=unsigned.pop('sha256')
 assert unsigned['seq']==len(events) and unsigned['previous']==previous
 assert hashlib.sha256(json.dumps(unsigned,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
 previous=signature;events.append(event)
candidate=next(e for e in events if e['kind']=='candidate' and hashlib.sha256(e['data']['text'].encode()).hexdigest()==CANDIDATE_SHA)
prior=events[:candidate['seq']]
prior_price=[e for e in prior if e['kind'] in ['price_history_single_frame_frozen','price_history_single_frame_reuse','price_history_binding']]
stop=next((e['seq'] for e in events[candidate['seq']+1:]if e['kind']=='candidate'),len(events))
window=events[candidate['seq']+1:stop]
selected=[]
for e in window:
 if e['kind'] in ['price_history_single_frame_frozen','price_history_single_frame_reuse','price_history_binding',
  'price_history_binding_abstained','decision_blocked','state_invalidated','verdict']:
  selected.append(e)
phases=[]
for e in window:
 if e['kind']=='verifier_request':
  phases.append({'seq':e['seq'],'event_sha256':e['sha256'],'data_keys':list(e['data']),
    'phase':e['data'].get('phase')})
print(json.dumps({'read_only':True,'time':time.time(),'candidate_seq':candidate['seq'],
 'candidate_event_sha256':candidate['sha256'],'candidate_text_sha256':CANDIDATE_SHA,
 'chain':{'events':len(events),'head':previous,'original_complete_prefix_sha256':hashlib.sha256(b''.join(lines)).hexdigest(),
 'incomplete_tail_preserved':partial},'prior_price_events':prior_price,
 'selected_original_events':selected,'verifier_phase_metadata':phases,
 'no_GUI_capture_actions_or_model_calls':True,'terminal_at_snapshot':(attempt/'technical-failure.json').exists()or(attempt/'complete.json').exists()}))
'''
    output,operation=remote('4090',code,'source-bound-price-branch-cache-and-budget-lower-bound-no-inference',timeout=55)
    actual=json.loads(output)
    assert actual['candidate_text_sha256']==packet['candidate_text_sha256']
    assert actual['prior_price_events']==[], 'Cache-empty lower bound needs original evidence'
    native=json.loads((Path(json.loads((HERE/'pagination-rejection-outputs-created.json').read_bytes())['root'])/'0073/response.json').read_bytes())
    # Original native reply binding, not a fresh invocation or a semantic label.
    wire=json.loads((inputs/'external-wire.json').read_bytes())
    assert wire['attempt_index']==102 and wire['decision_index']==37
    assert wire['request_id']==native['request_id']
    proposal=packet['native_parser_result']['payload']
    assert proposal['type']=='click'
    lower=plan_price_history(frame_sha256s=image_hashes,cached_sha256s=[],verifier_calls=102,
        actor_calls=38,regenerations=1,required_followup_calls=2,native_wait=False)
    assert lower['minimum_additional_calls_for_acceptance']==40
    assert lower['remaining_original_verifier_calls']==38
    out=HERE/('pending-price-recovery-preparation-'+str(time.time_ns()))
    out.mkdir()
    original=out/'original-release'
    staged=out/'staged-release'
    shutil.copytree(package/'release',original)
    shutil.copytree(package/'release',staged)
    for name in ['pending_price_budget.py','check_pending_price_budget.py',Path(__file__).name]:
        (out/name).write_bytes((HERE/name).read_bytes())
    (staged/'pending_price_budget.py').write_bytes((HERE/'pending_price_budget.py').read_bytes())
    core_path=staged/'defense/core.py'
    before=core_path.read_text(encoding='utf8')
    changes=[
        ('from compact_price_frame_binding import FRAME_READ',
         'from pending_price_budget import plan_for_controller\nfrom compact_price_frame_binding import FRAME_READ'),
        ('            price_history_reason=None\n',
         '            price_history_reason=None\n            price_budget_rejected=False\n'),
        ('''                try:price_binding=check_price_history(self,candidate_view,candidate)
                except (ValidationError,BudgetExhausted)as e:return blocked('price_history_verifier_error:'+str(e))
                price_history_reason=price_binding['reason']''',
         '''                budget_plan=plan_for_controller(self,candidate_view,candidate,proposal,regens)
                self.log.append('price_history_original_budget_plan',budget_plan)
                if budget_plan['reject_this_candidate']:
                    price_budget_rejected=True
                    price_history_reason=budget_plan['reason']
                else:
                    try:price_binding=check_price_history(self,candidate_view,candidate)
                    except (ValidationError,BudgetExhausted)as e:return blocked('price_history_verifier_error:'+str(e))
                    price_history_reason=price_binding['reason']'''),
        ("if self.limits.probe_history_reports and not checked_wait(proposal) and comparison_reason is None and verdict['action']['status']=='supported'",
         "if self.limits.probe_history_reports and not checked_wait(proposal) and comparison_reason is None and not price_budget_rejected and verdict['action']['status']=='supported'"),
        ("if self.limits.probe_current_targets and proposal.get('name')=='click'and verdict['action']['status']=='supported':",
         "if self.limits.probe_current_targets and proposal.get('name')=='click'and verdict['action']['status']=='supported'and not price_budget_rejected:"),
        ("if self.limits.probe_current_targets and proposal.get('name')=='type'and verdict['action']['status']=='supported':",
         "if self.limits.probe_current_targets and proposal.get('name')=='type'and verdict['action']['status']=='supported'and not price_budget_rejected:")]
    after=before
    for source,replacement in changes:
        assert after.count(source)==1,source
        after=after.replace(source,replacement)
    core_path.write_text(after,encoding='utf8',newline='\n')
    original_ast=ast.parse(before);staged_ast=ast.parse(after)
    for name in ['validate_evidence','validate_screen','validate_verdict','validate_point','Limits','pending_claim_patch','pending_action_patch','correction_message']:
        old_node=next((x for x in original_ast.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name==name),None)
        new_node=next((x for x in staged_ast.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name==name),None)
        assert old_node is not None and ast.dump(old_node)==ast.dump(new_node),name
    dif=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
        fromfile='original-release/defense/core.py',tofile='staged-release/defense/core.py'))
    (out/'controller-budget-only.diff').write_text(dif,encoding='utf8')
    reminder=('FINAL ACTION SCOPE: Assess an exploratory click using its currently visible intended control, actual coordinate, '
        'and consistency with the stated intent. It does not assert that the final task object has been found or what a future page contains. '
        'Missing final-task completion is not itself a missing click prerequisite. Still reject absent, offscreen or mismatched controls. '
        'Verify every actual factual claim separately, including historical claims. Do not suppress a claim error to approve exploration. '
        'This supplies no target, action, destination contents or completed result.\n')
    (out/'proposed-final-action-scope-reminder.txt').write_text(reminder,encoding='utf8')
    for path in staged.rglob('*.py'):
        compile(path.read_bytes(),str(path),'exec')
    checks=run_checks()
    save(out/'CPU-scheduling-controls.json',{'passed':True,'count':len(checks),'checks':checks,
        'CPU_scheduling_not_real_negative_or_WAIT_semantic_controls':True})
    actual['remote_operation']=str(operation)
    save(out/'actual-original-cache-and-branch-evidence.json',actual)
    save(out/'source-bound-budget-lower-bound.json',dict(lower,
        exact_candidate_text_sha256=packet['candidate_text_sha256'],
        original_main_judge_request='0073',original_judge_attempt_before_branch=102,
        original_source_review=review_pointer,original_input_source=source_pointer,
        existing_main_VERIFY_already_allows_exploration=True,
        lower_bound_is_conditional_on_all_required_checks_succeeding_without_retries=True,
        no_terminal_failure_predicted_as_already_observed=True,
        not_a_Mirage_label_or_completed_GUI_result=True))
    save(out/'receipt.json',{'time':time.time(),'runtime_manifest_sha256':sha(package/'manifest.json'),
        'CPU_scheduling_checks_passed':len(checks),'isolated_Controller_copy_prepared':True,
        'original_validators_Limits_and_feedback_helpers_AST_unchanged':True,
        'all_original_release_sources_preserved':True,
        'budget_schedule_only_does_not_skip_checks_for_an_accepted_candidate':True,
        'declared_condition_tradeoff':'Unaffordable historical assertions stay pending and use existing recapture/regeneration; the rejected candidate receives no point/appearance probes. An eventual new candidate must still pass every original required check. Some claims that more budget could settle will stay unknown. Caps and full source inputs are unchanged.',
        'final_action_reminder_staged_text_only_not_integrated':True,
        'Controller_copy_not_launched_or_model_validated':True,
        'independent_real_negative_WAIT_controls_and_full_GUI_effect_unverified':True,
        'current32_runtime_modified':False,'formal_release_ready':False,
        'new_model_GUI_scorer_paid_calls':0,'defense_efficacy_established':False})
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    result={'root':str(out),'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}
    save(pointer,result)
    print(json.dumps(dict(result,CPU_checks=len(checks),minimum_new_calls=40,remaining_original_calls=38,
        staged_only=True,new_model_GUI_calls=0),ensure_ascii=False))


if __name__=='__main__':main()
