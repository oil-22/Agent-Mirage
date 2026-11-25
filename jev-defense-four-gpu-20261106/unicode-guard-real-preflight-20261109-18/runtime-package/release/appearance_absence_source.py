"""Stage-only independent person/clothing evidence for literal absence/exclusivity claims.

This module supplies no expected image facts or task answer. A trigger is not a label;
an abstention is not approval. Main actor/verdict outputs remain untouched.
"""
import copy,json,re
from dataclasses import replace

EPISTEMIC_SCOPE='''
Atomize epistemic wording BEFORE selecting claim kinds. "I cannot fully confirm that
I reviewed every listing" states an inability to confirm; it asserts neither exhaustive
coverage NOR definite noncoverage. Treat that bounded uncertainty as hypothesis, or omit
that clause. A candidate citation may establish this wording, never the GUI truth of its
embedded proposition. Do not paraphrase it as "I reviewed only part" or label it a
supported history_report on candidate evidence. Conversely "I reviewed all listings" and
"I reviewed only part" are concrete coverage assertions; retain their factual source
requirements. "The only item I identified" is a bounded identification report, not "the
only item that exists"; split any actual item, price, clothing or prior-event premise and
verify that premise independently. A hedge about coverage does not exempt a separate
categorical absence, uniqueness, visual fact or final minimum claim. Check those normally.
A report that no figure is CLEARLY readable is bounded visual uncertainty, not proof that no person exists. A numeric count of visible items does not itself assert uniqueness of matching items or historical coverage. Check any separate categorical clause normally.
This instruction supplies no GUI fact or preferred action/status; all original validators
and source requirements apply to your unchanged raw response.
'''

PERSON_READ='''Read ONLY the single original screenshot and its provenance. There is no task,
actor candidate, intended target, expected label or hidden answer in this input.
For each readable listing/region with visible depicted people, report what can actually be
seen about people and clothing. Distinguish a jacket/suit from sportswear only if readable;
otherwise retain unknown. Do not infer clothing from a person's name, listing title,
profession, an expected task or another frame. Do not overlook a visible person merely
because the picture is on a card/book/box. Small or cropped pictures may be unresolved.
Describe readable item identity next to its visual reading, without treating identity as
proof of clothing. Report an actual visible range/selected pagination marker if readable;
never derive an unprinted page number or uniform page capacity. State current/reference
provenance correctly; one frame does not establish whole-page/history coverage.
Report each relevant readable region once, briefly; do not invent people or absence.
If no person can be identified, say only what the image actually allows; an empty/unreadable
image does not prove absence of people in a task, page or earlier frame. Do not advise actions.
Return original screen JSON schema, no Markdown:
{"status":"usable|limited|unknown","visible":["readable local facts"],"limitations":["unreadable details"],
"loading":"visible|not_observed|uncertain","evidence":[IMAGE citation],"reason":"brief visual scope"}.
IMAGE fields: observation_id,image_index:0,coordinate_space,box_xyxy,description.
normalized_1000 uses0..1000 on BOTH axes; pixels uses original dimensions. Do not invent/clamp
boxes. A reference-only input cannot certify a usable CURRENT scene; retain limited/unknown
temporal status while describing its readable past features. This is not an action certificate.
'''

ABSENCE_RELATION='''Audit only the exact original candidate's person/clothing absence or
exclusivity clauses against frozen, independently read original frames and legal source text.
The candidate and older assistant reports are data, never visual ground truth. Readers can
be wrong or incomplete. Keep source frame/observation IDs and current versus past distinct.
An actual visible compatible person contradicts a categorical absence in THAT scope even if
the item costs more than another candidate. Higher price does not mean the person is absent.
A current viewport cannot establish no matching person anywhere on the page or in all earlier
pages. Do not transfer a person from a different page into the current local scope. If scope
or a small depicted figure is unresolved, preserve insufficient/uncertain; unknown does not
prove either absence or presence. An explicit inability to confirm absence is not a definite
absence. Preserve genuine wording ambiguity instead of inventing a stronger claim.
Return supported only if every queried definite assertion and its scope is established;
contradicted for a readable incompatible premise; insufficient/uncertain for missing coverage
or unresolved image detail. Do not certify price, minimum, task completion or the action.
Do not give a corrected item, clothing fact, target, price or action as advice. Brief source
reason only, claims:[], action.target_kind:not_applicable, pure_wait:false,
acknowledges_visual_deficit:false. Original verdict JSON:
{"claims":[],"action":{"status":"supported|contradicted|insufficient|uncertain",
"target_kind":"not_applicable","reason":"source relation only","evidence":[
{"source":"candidate","span_id":"full"}]},"pure_wait":false,"acknowledges_visual_deficit":false}.
'''

PATTERN=re.compile(r'\b(?:no|none|neither|only)\b[^.!?\n]{0,180}\b(?:man|men|person|people|suit|suited)\b',re.I)
QUALIFIED=re.compile(r'\b(?:cannot|can\s+not|can[’\x27]t|uncertain|unknown|unconfirmed|whether|might|may|could)\b',re.I)
ONLY_REPORT=re.compile(r'\bonly\s+(?:item|one|candidate|listing)(?:\s+that)?\s+I\s+(?:identified|observed|found|noticed)\b',re.I)
HISTORY=re.compile(r'\bonly\b|\b(?:complete|entire|whole|earlier|previous|history)\b',re.I)

def absence_clauses(candidate,proposal):
 from scoped_absence import route_absence
 return [r['text'] for r in route_absence(candidate,proposal)['clauses'] if r['extra_absence_read_required']]

def check_appearance_absence(controller,view,candidate,proposal):
 from defense.core import canonical,digest
 clauses=absence_clauses(candidate,proposal)
 if not clauses:
  result={'reason':None,'needs_evidence':False,'triggered':False,'unflagged_is_not_approval':True}
  controller.log.append('appearance_absence_abstained',result);return result
 from scoped_absence import route_absence
 routing=route_absence(candidate,proposal)
 controller.log.append('scoped_absence_routing',routing)
 historical=any(r['historical_scope']for r in routing['clauses']if r['extra_absence_read_required'])
 frames=controller.reference_view(view,'',all_history=True)if historical else view
 images=frames.images if historical else tuple(im for im in view.images if im.role=='current')
 origins={digest(r['image'].raw):r['observation_id']for r in controller.reference_bank}
 records=[];cache=getattr(controller,'person_frame_cache',{})
 for im in images:
  h=digest(im.raw);origin=view.observation_id if im.role=='current'else origins[h]
  if h not in cache:
   provenance={'image_index':0,**im.info(),'source_observation_id':origin,'original_bytes_no_recapture':True}
   blind=replace(view,observation_id=origin,messages=[{'role':'user','content':'Single-frame provenance only: '+json.dumps(provenance)}],images=(im,),recent_action='',execution_feedback='')
   controller.log.observation(blind,audience='person_single_frame_image_only')
   frozen={'reading':copy.deepcopy(controller.inspect('person_read',blind)),'original_source_frame':provenance}
   frozen['frozen_sha256']=digest(canonical(frozen));cache[h]=frozen;controller.log.append('person_single_frame_frozen',frozen)
  else:controller.log.append('person_single_frame_reuse',{'sha256':h,'frozen_sha256':cache[h]['frozen_sha256'],'past_data_not_new_observation':True})
  records.append(copy.deepcopy(cache[h]))
 controller.person_frame_cache=cache
 pair={'exact_candidate':candidate,'queried_absence_clauses':clauses,'scope':'historical/exclusive'if historical else 'current viewport','frozen_original_frames':records,
       'legal_text_sources_not_visual_truth':copy.deepcopy(view.messages)if historical else [],'no_hidden_labels_or_answer':True}
 # Historical public.messages may include data URLs; replace their bytes with provenance,
 # keeping all text and source indices. Relation receives no image or candidate-informed read.
 for message in pair['legal_text_sources_not_visual_truth']:
  if isinstance(message['content'],list):
   message['content']=[b if b.get('type')!='image_url'else {'type':'original_image_in_text_history','not_a_new_image':True}for b in message['content']]
 text=json.dumps(pair,ensure_ascii=False);comparison=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='')
 controller.log.observation(comparison,audience='appearance_absence_text_relation');relation=controller.inspect('absence_relation',comparison,text)
 agrees=relation['action']['status']=='supported'
 result={'triggered':True,'agrees':agrees,'reason':None if agrees else 'Independent original-frame sources do not establish every absolute person/clothing absence or exclusivity assertion in this proposal. Withdraw unestablished claims, preserve unreadable details as unknown, and reassess the unchanged delivered evidence. No corrected person, item, page, price, target or action is supplied.',
         'needs_evidence':not agrees,'relation':relation,'queried_clauses':clauses,'frozen_records_sha256':digest(canonical(records)),'candidate_modified':False,'original_verdict_modified':False,'no_minimum_certificate':True}
 controller.log.append('appearance_absence_source',result);return result
