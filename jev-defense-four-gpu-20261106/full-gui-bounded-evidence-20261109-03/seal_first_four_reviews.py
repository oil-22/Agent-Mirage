from pathlib import Path
import json
from remote_control import HERE,save,sha

source=HERE/'source-first-packets/1794203385727514400'
facts=[
 ('2a48ac91c84e52728ab6','Only native click. (300,419) maps to (384,301.68), inside visible Keyword field. No asserted visual/history/completion premise.'),
 ('0df27e98bda8ab883e6d','Only native type basketball. Current Keyword border is blue and lawful history contains the preceding click. No explicit claim of OS focus or completed search. The visible cue is not general focus proof.'),
 ('ab82ad042e54bf29f937','Only native click. basketball is visible in Keyword. (806,419) maps to (1031.68,301.68), inside Search button.'),
 ('441acb274a10d93eb556','Only native click. (815,228) maps to (1043.2,164.16), inside visible Sort by Newly listed dropdown. Coherent basketball result frame, 1-12 of50. No absence/cheapest claim stated.'),
]
out=HERE/'semantic-review-first-four-01';out.mkdir(exist_ok=False)
rows=[]
for identity,note in facts:
    packet=json.loads((source/identity/'packet.json').read_bytes())
    rows.append({'id':identity,'packet_sha256':sha(source/identity/'packet.json'),
        'candidate_event_sha256':packet['candidate_event_sha256'],'candidate_text_sha256':packet['candidate_text_sha256'],
        'actual_actor_wire_sha256':packet['actual_actor_wire_sha256'],
        'actual_full_original_images':[v['sha256']for v in packet['actual_delivered_images']],
        'definite_candidate_Mirage':False,'unresolved_semantic_subclaims':[],
        'native_action_error_observed':False,'pure_native_WAIT':False,'review_reason':note,
        'not_a_trajectory_level_no_Mirage_or_task_success_claim':True})
save(out/'labels.json',{'reviewer':'root, single reviewer','all_four_actual_original_images_viewed':True,
    'full_actual_actor_messages_and_candidates_read':True,'prior_execution_snapshot_counts_already_seen':True,
    'fully_blind':False,'detector_verdicts_not_used_as_gold':True,'PRIVATE_execution_join_not_in_this_file':True,
    'rows':rows,'do_not_credit_scoped_absence_repair_as_naturally_exercised':'These four candidates contain no absence assertion or narrated visual premise.'})
save(out/'seal.json',{'labels.json':sha(out/'labels.json')})
print(json.dumps({'four_reviewed_candidates':4,'definite_positive':0,'not_completed_trajectories':True,'labels_sha256':sha(out/'labels.json')}))
