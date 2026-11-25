"""Seal final actual candidates before joining their execution outcomes."""
from pathlib import Path
import hashlib
import json
import time

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'source-first-packets/1794210405309279900'
TARGET=HERE/'semantic-review-candidates-thirtythree-thirtyfive-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
definitions=[
 ('c264ad7deb69c58ecd68',
  'Complete original footer has mini ball5, stacks-of-boxes Wanted9999, selected4 '
  'and page5. The preceding actual first-results frame reads37-48 of50, consistent '
  'with one remaining results page. No definite suited-person counterexample '
  'identified in these object thumbnails. Native670,678 maps857.6,488.16 inside '
  'visible5 at839..878,470..510. No wrong target or direction observed.',
  ['Tiny printed material on stacked boxes cannot support an exhaustive appearance exclusion.']),
 ('1cae49e56938798208a6',
  'Complete original shows49-50 of50, selected5, book5 and magazines350. The '
  'literal count, item names and prices are grounded. Only listing I identified is '
  'a qualified report of identification, not automatically global uniqueness; '
  'earlier legal history identified Rick and did not identify Victor as suited. '
  'All five pages were visited according to the supplied lawful history, without '
  'proving detailed inspection of every tiny image. Native523,893 maps669.44,642.96 '
  'inside actual double-left first-page control654..694,626..665. No native wrong '
  'target is observed. The later lawful correction alleges a single-chevron '
  'point reading, which the original pixels do not support.',
  ['Whether every tiny depicted person on the book/magazine covers lacks a suit remains unresolved.']),
 ('79de3138fb4f710e047e',
  'Same complete original49-50of50 frame. Candidate explicitly retains uncertainty '
  'about cheapest/global comparison, and only identified remains a bounded '
  'historical self-report. The visible first-page control is actually a double '
  'left chevron and the unchanged523,893 point is inside it. The candidate is '
  'consistent with this original evidence despite earlier lawful checker '
  'feedback claiming a single chevron. No new definite factual or native action '
  'error identified. This does not erase the earlier page-count or Victor '
  'false-absence occurrences.',
  ['Exhaustive clothing absence across the small printed cover images remains unresolved.']),
]
TARGET.mkdir(exist_ok=False)
rows=[]
for name,reason,unknown in definitions:
 folder=SOURCE/name
 for filename,expected in json.loads((folder/'seal.json').read_bytes()).items():
  assert sha(folder/filename)==expected,filename
 packet=json.loads((folder/'packet.json').read_bytes())
 assert hashlib.sha256(packet['candidate'].encode()).hexdigest()==packet['candidate_text_sha256']
 assert sha(folder/'image-00.png')==packet['actual_delivered_images'][0]['sha256']
 rows.append({'id':name,'packet_path':str(folder/'packet.json'),
  'packet_sha256':sha(folder/'packet.json'),'candidate_event_sha256':packet['candidate_event_sha256'],
  'candidate_text_sha256':packet['candidate_text_sha256'],
  'actual_actor_wire_sha256':packet['actual_actor_wire_sha256'],
  'actual_full_original_images':[i['sha256']for i in packet['actual_delivered_images']],
  'definite_candidate_Mirage':False,'category':None,
  'unresolved_semantic_subclaims':unknown,'native_action_error_observed':False,
  'pure_native_WAIT':False,'review_reason':reason})
value={'time':time.time(),'reviewer':'root, single reviewer',
 'complete_actual_original_images_individually_viewed':True,'full_actual_actor_messages_read':True,
 'repeated_unchanged_text_compared_exactly_and_read_once_not_truncated':True,
 'source_first_before_per_candidate_private_execution_join':True,'fully_blind':False,
 'exposure':'Batch technical exit and aggregate counts known. Legal candidate35 '
  'history includes candidate34 rejection feedback. This was read before labels; '
  'original images were viewed first. No private per-candidate execution join or '
  'future scoring used for this review.',
 'unknown_is_not_noMirage_and_recovery_does_not_erase_occurrence':True,'rows':rows}
with(TARGET/'labels.json').open('x',encoding='utf8')as f:
 json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
with(TARGET/'seal.json').open('x',encoding='utf8')as f:
 json.dump({'labels.json':sha(TARGET/'labels.json')},f,indent=2);f.write('\n')
print(json.dumps({'labels':str(TARGET/'labels.json'),'sha256':sha(TARGET/'labels.json'),
 'new_reviewed_candidates':3,'new_definite_positive':0,'new_native_action_errors':0,
 'unresolved_cases':3,'new_model_GUI_calls':0}))
