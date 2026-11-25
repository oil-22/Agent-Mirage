"""Boundary checks on routing, source binding and immutability, not model accuracy."""
import copy,io,unittest
from PIL import Image
from defense.core import PublicView,VisibleImage,ValidationError
from carryover_feedback_routing import build_feedback


class RoutingBoundaries(unittest.TestCase):
    def setUp(self):
        b=io.BytesIO();Image.new('RGB',(1280,720),'white').save(b,format='PNG')
        self.view=PublicView('now',[{'role':'system','content':'native system'},
             {'role':'user','content':'Task'}, {'role':'assistant','content':"I'm on page 4. <action>{\"type\":\"scroll\",\"direction\":\"down\"}</action>"}],(VisibleImage(b.getvalue(),'current'),))
        self.claim={'id':'c1','kind':'gui_fact','text':"I'm on page 4",'status':'supported',
             'evidence':[{'observation_id':'now','image_index':0,'coordinate_space':'normalized_1000','box_xyxy':[300,200,450,250],'description':'Header reads25 - 36 of 50 listings,12-per-page.'}],
             'reason':'Current page4 at12-per-page.','dependent_decisions':[]}
        self.verdict={'claims':[self.claim],'action':{'status':'insufficient','target_kind':'not_applicable','reason':'historical action, not evaluated as a new proposal','evidence':[]},'acknowledges_visual_deficit':False,'pure_wait':False}
    def run_case(self):return build_feedback(self.view,2,self.verdict)
    def test_inconsistent_supported_not_forwarded(self):
        d=self.run_case()['data'];self.assertFalse(d['supported_current_reuse']);self.assertEqual(len(d['quarantined_checker_support']),1)
    def test_original_status_retained_for_audit(self):self.assertEqual(self.run_case()['validated_original_verdict']['claims'][0]['status'],'supported')
    def test_inputs_not_edited(self):
        old=copy.deepcopy(self.verdict);before=copy.deepcopy(self.view.messages);self.run_case();self.assertEqual(old,self.verdict);self.assertEqual(before,self.view.messages)
    def test_not_infer_corrected_page(self):self.assertNotIn('page 3',self.run_case()['feedback'])
    def test_original_validator_rejects_bad_box(self):
        self.claim['evidence'][0]['box_xyxy']=[300,200,450,1200]
        with self.assertRaises(ValidationError):self.run_case()
    def test_original_validator_rejects_wrong_observation(self):
        self.claim['evidence'][0]['observation_id']='old'
        with self.assertRaises(ValidationError):self.run_case()
    def test_original_validator_rejects_missing_current_source(self):
        self.claim['evidence']=[]
        with self.assertRaises(ValidationError):self.run_case()
    def test_not_read_future_candidate(self):
        with self.assertRaises(ValueError):build_feedback(self.view,3,self.verdict)
    def test_not_audit_user_text_as_report(self):
        with self.assertRaises(ValueError):build_feedback(self.view,1,self.verdict)
    def test_boolean_not_accepted_as_index(self):
        with self.assertRaises(ValueError):build_feedback(self.view,True,self.verdict)
    def test_older_assistant_not_selected(self):
        self.view.messages.append({'role':'assistant','content':'A newer real report'})
        with self.assertRaises(ValueError):self.run_case()
    def test_consistent_support_preserved_without_truth_upgrade(self):
        self.claim['text']="I'm on page 3";d=self.run_case()['data'];self.assertEqual(len(d['supported_current_reuse']),1);self.assertTrue(d['unflagged_is_not_semantic_approval'])
    def test_missing_capacity_is_not_guessed(self):
        self.claim['evidence'][0]['description']='25 - 36 of 50';self.claim['reason']='range visible';d=self.run_case()['data'];self.assertFalse(d['quarantined_checker_support']);self.assertEqual(d['supplementary_checks'][0]['status'],'not_checkable')
    def test_insufficient_never_promoted(self):
        self.claim['status']='insufficient';d=self.run_case()['data'];self.assertFalse(d['supported_current_reuse']);self.assertEqual(d['pending_current_reuse'][0]['original_judge_status'],'insufficient')
    def test_no_budget_or_execution(self):
        r=self.run_case();self.assertEqual(r['new_model_calls'],0);self.assertEqual(r['additional_budget'],0);self.assertFalse(r['actor_or_action_executed'])


if __name__=='__main__':unittest.main()
