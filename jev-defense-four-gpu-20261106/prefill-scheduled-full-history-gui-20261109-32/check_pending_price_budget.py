"""CPU adversarial scheduling controls, not real visual/WAIT model controls."""
import copy
import hashlib
from pending_price_budget import plan_price_history


def run_checks():
    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(37)]
    base = dict(frame_sha256s=hashes,cached_sha256s=[],verifier_calls=102,
                actor_calls=38,regenerations=1,required_followup_calls=2,native_wait=False)
    checks = []

    def case(name, changes, predicate):
        params = copy.deepcopy(base)
        params.update(changes)
        before = copy.deepcopy(params)
        result = plan_price_history(**params)
        assert predicate(result), (name,result)
        assert params == before, 'Input was edited: '+name
        assert result['semantic_evidence_approved'] is False
        assert result['automatic_allow_or_execute'] is False
        assert result['candidate_action_or_verdict_rewritten'] is False
        checks.append(name)

    case('actual37unique frames need40additional but only38remain',{},
         lambda r:r['minimum_additional_calls_for_acceptance']==40 and r['route']=='retain_pending_and_regenerate')
    case('exact lower bound is scheduled but never certified fit',{'verifier_calls':100},
         lambda r:r['route']=='read_all_original_frames_and_relation' and r['minimum_is_not_a_fit_guarantee'])
    case('one below lower bound remains pending',{'verifier_calls':101},lambda r:r['reject_this_candidate'])
    case('all frames cached still require relation and current point alignment',{'cached_sha256s':hashes,'verifier_calls':137},
         lambda r:r['minimum_additional_calls_for_acceptance']==3 and r['required_relation_calls']==1)
    case('cached evidence is not free relation',{'cached_sha256s':hashes,'verifier_calls':138},lambda r:r['reject_this_candidate'])
    case('duplicate original bytes cost one independent read',{'frame_sha256s':[hashes[0]]*37,'verifier_calls':136},
         lambda r:r['missing_original_frame_reads']==1 and r['minimum_additional_calls_for_acceptance']==4)
    case('foreign cache entries cannot substitute missing source frames',{'cached_sha256s':['f'*64]},
         lambda r:r['missing_original_frame_reads']==37 and r['reject_this_candidate'])
    case('no images never certifies unsupported history',{'frame_sha256s':[],'verifier_calls':0},lambda r:r['reject_this_candidate'])
    case('last actor budget cannot invent regeneration',{'actor_calls':70},
         lambda r:r['route']=='retain_pending_original_recovery_exhausted')
    case('second regeneration cannot create a third',{'regenerations':2},
         lambda r:r['route']=='retain_pending_original_recovery_exhausted')
    case('fully exhausted judge budget remains pending',{'verifier_calls':140},lambda r:r['reject_this_candidate'])
    case('native WAIT keeps its original price-branch abstention',{'native_wait':True,'verifier_calls':140},
         lambda r:r['route']=='native_wait_price_branch_abstention' and r['pure_native_WAIT_Mirage_exclusion_unchanged'])
    case('typing focus followup still reserved',{'required_followup_calls':1},
         lambda r:r['minimum_additional_calls_for_acceptance']==39 and r['reject_this_candidate'])
    case('a rejected exploration proposal is not silently executed',{},lambda r:r['current_candidate_cannot_reach_acceptance'])
    for name,changes in [
        ('noexpandedjudgecap',{'verifier_calls':141}),
        ('noexpandedactorcap',{'actor_calls':71}),
        ('noexpandedregencap',{'regenerations':3}),
        ('negativecount',{'verifier_calls':-1}),
        ('booleanisnotintegerbudget',{'verifier_calls':True}),
        ('unboundframesrejected',{'frame_sha256s':['image-1']}),
        ('unboundcacherejected',{'cached_sha256s':['image-1']}),
        ('WAITmustbenativeboolean',{'native_wait':1})]:
        params=copy.deepcopy(base);params.update(changes)
        try:plan_price_history(**params)
        except ValueError:checks.append(name)
        else:raise AssertionError('Invalid input accepted: '+name)
    return checks


if __name__ == '__main__':
    import json
    checks=run_checks()
    print(json.dumps({'passed':True,'count':len(checks),'checks':checks,
                      'new_model_GUI_scorer_calls':0,'CPU_scheduling_not_semantic_controls':True}))
