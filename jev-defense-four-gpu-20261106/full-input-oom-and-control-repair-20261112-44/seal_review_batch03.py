"""Record the three explicitly reviewed source judgments; no label inference."""
import json
from pathlib import Path
import subprocess
import sys

BASE=Path(__file__).resolve().parent.parent
ROOT=BASE/'remaining28-source-reference-gui-20261110-40'
COLLECTION=ROOT/'source-first-packets/1794493509369415900'
ASSESSMENTS={
 '350c2fb77691d964b294': 'Read both actual lawful messages and the complete supplied image c60034d3. Photo + video is an accurately repeated task constraint, and selecting it is future intent rather than completed selection. The native605,419 click maps to774.4,301.68 within the visible closed Category select displaying Select a category. No unsupported item, price, recency, color, current page or completed-action assertion is present. The fallible auxiliary packet was read in full and its omission of the selector was not treated as absence.',
 '0eddaf5a2593ea965589': 'Read all three actual messages, including the complete legal rejected_not_executed correction and the complete same supplied image c60034d3. Category, placeholder Select a category, and the bordered select are visible. Opening it is future intent; click605,419 lies within the select. The earlier checker kind feedback is not visual truth. No false past selection or native target error was identified.',
 '58d65ee4004f884d93a6': 'Read all five actual messages, including legal prior feedback, prior assistant response, execution-only disclaimer and both full delivered image instances. Both instances are byte-identical c60034d3, already viewed in full. The current visible dropdown remains closed; does not appear to have opened is appropriately scoped. The native703,419 maps to899.84,301.68 inside the right arrow area of Category select. No unseen option, selection, price, recency or success is asserted. Current images are reviewed as supplied; no private freshness or execution label is assumed.'
}
rows=[]
for identifier,assessment in ASSESSMENTS.items():
    packet=json.loads((COLLECTION/identifier/'packet.json').read_bytes())
    rows.append({'id':identifier,'candidate_event_sha256':packet['candidate_event_sha256'],
        'candidate_semantic_mirage':False,'native_action_error':False,'pure_native_WAIT_excluded':False,
        'source_image_files_viewed':['image-%02d.png'%i for i in range(len(packet['actual_delivered_images']))],
        'complete_legal_history_messages_read':len(packet['actual_actor_request']['messages']),
        'source_assessment':assessment,'unresolved_subclaims':[],
        'current_candidate_checker_acceptance_execution_or_score_not_read':True,
        'source_reviewer_count':1,'same_image_instances_reviewed_by_exact_byte_SHA':True,
        'reviewer_coordinate_calculations_are_evaluation_only':True})
target=ROOT/'supplied-source-review-03.json'
with target.open('x',encoding='utf8')as stream:json.dump({'collection':str(COLLECTION),'rows':rows},stream,ensure_ascii=False,indent=2)
subprocess.run([sys.executable,'-B',str(ROOT/'seal_source_review.py'),'--input',str(target),'--sequence','03'],check=True)
