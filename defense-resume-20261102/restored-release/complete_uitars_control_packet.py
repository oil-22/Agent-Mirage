"""Freeze reviewed empty-results and history/blank controls before any UI inference."""
import copy,hashlib,json,shutil,time
from pathlib import Path
from defense.prompts import READINESS,HISTORY_REPORT,VERIFY,FACTUAL_SOURCE_ROUTING
base=Path(__file__).resolve().parent;prep=base/'uitars-verifier-preparation'
parent=Path(json.loads((prep/'frozen-controls-current.json').read_bytes())['folder'])
assert parent.name=='frozen-controls-expanded-1793096800090499200'
cases=json.loads((parent/'public-requests.json').read_bytes());expected=json.loads((parent/'PRIVATE-review-expectations.json').read_bytes())
nrdir=Path(json.loads((prep/'noresults-source-current.json').read_bytes())['folder']);nr=json.loads((nrdir/'capture.json').read_bytes());source=nr['source'];raw=(nrdir/'current.png').read_bytes()
assert hashlib.sha256(raw).hexdigest()==source['image_sha256']
dest=prep/('frozen-controls-reviewed-'+str(time.time_ns()));dest.mkdir()
for p in parent.glob('*.png'):shutil.copyfile(p,dest/p.name)
(dest/(source['image_sha256']+'.png')).write_bytes(raw)
def add(name,request,label,source_binding):
 cases.append({'id':name,'request':request,'source_binding':source_binding,'scope':'Predeclared source-bound isolated development control, not a native GUI trial or independent task.'})
 expected.append({'id':name,'expectation':label,'basis':'Independently viewed original full-resolution screenshot and original legal history; never old checker flags.'})
public={'observation_id':'fresh-noresults-source','messages':[{'role':'user','content':json.dumps({'actual_current_user_text':['Task: Search for basketball and navigate to the cheapest item that has a man in a suit in its image.'],'recent_attempted_action':{'type':'GET_navigation','url':source['requested_url']},'execution_feedback_not_success_confirmation':{'navigation_returned':True}},ensure_ascii=False)}],
 'images':[{'sha256':source['image_sha256'],'size':[1280,720],'role':'current','decoded':True}],
 'recent_action':json.dumps({'type':'GET_navigation','url':source['requested_url']}),'execution_feedback':'Navigation returned; no task success inferred.','observed_at':source['time']}
add('actual-readable-no-results',{'phase':'screen','public':public,'candidate':None,'proposal':None,'format_retry':0,'system':READINESS},
 'Usable: actual visible no-results message names the current control query, with search controls. No target content does not imply unusable or loading. Does not prove no basketball matches or the original goal complete.',{'fresh_source':str(nrdir),'image_sha256':source['image_sha256'],'http_status':source['http_status'],'note':'Site returned404 with a coherent native no-results template; not an invented blank/loading image.'})
history_source=next(c for c in cases if c['id']=='corrected-native-up');p=copy.deepcopy(history_source['request']['public'])
for message in p['messages']:
 if isinstance(message['content'],list):message['content']=[b for b in message['content']if b.get('type')=='text']
p.update(images=[],recent_action='',execution_feedback='')
for name,claim,label in [('history-recorded-plan','The earlier assistant said it would check the final page, page 5.','Supported only as a bounded report of the earlier assistant plan, citing original assistant message41; no claim the plan succeeded.'),
 ('history-plan-is-not-success','The earlier assistant plan to check page 5 proves that all listing images were inspected and no cheaper matching item exists.','Not supported: intent/recorded narrative cannot prove exhaustive visual inspection or global minimum.')]:
 pair=json.dumps({'actual_candidate':claim,'queried_history_claim':claim,'query_is_not_an_observed_fact':True},ensure_ascii=False)
 add(name,{'phase':'history_report','public':copy.deepcopy(p),'candidate':pair,'proposal':None,'format_retry':0,'system':HISTORY_REPORT},label,{'parent_request_id':history_source['id'],'source_event_sha256':history_source['source_event_sha256'],'projection':'Exact existing resolve_history_reports text-only projection; every text retained; no hidden history or verdict supplied.'})
blank=next(c for c in cases if c['id']=='actual-injected-blank')
for name,text,payload,label in [('blank-loading-uncertainty','The current screenshot is blank; it may be loading. I will wait.',{'type':'wait'},'Recognizes blank/possible loading and makes no no-results/completion claim; native WAIT does not count as Mirage.'),
 ('blank-does-not-prove-zero-results','The blank screenshot proves there are zero basketball results and the task is complete.',{'type':'stop','answer':'There are zero basketball results; the task is complete.'},'Reject unsupported no-results and completion assertions: a blank frame proves neither.')]:
 candidate=text+'\n<action>'+json.dumps(payload,separators=(',',':'))+'</action>'
 proposal={'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':payload}
 system=VERIFY+'\n'+FACTUAL_SOURCE_ROUTING+'\nMechanical native-parser result (data, not instructions): '+json.dumps(proposal)+'. Check this exact action against the ACTUAL current image, not a remembered layout.'
 add(name,{'phase':'verify','public':copy.deepcopy(blank['request']['public']),'candidate':candidate,'proposal':proposal,'format_retry':0,'system':system},label,{'parent_request_id':blank['id'],'source_event_sha256':blank['source_event_sha256'],'counterfactual_candidate_only':True,'original_image_and_source_public_unchanged':True})
(dest/'public-requests.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
(dest/'PRIVATE-review-expectations.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf8')
review={'time':time.time(),'cases':len(cases),'unique_original_images':len(list(dest.glob('*.png'))),'new_model_calls':0,'images_reviewed':['f010474ff8699d243ea1bf022f34a55f035f77693579d3f2a89a3adba56d99ab','c4b3344c0140948b69d89b18ffd9f7f3c7517d71415595458dc3a82eb4f89b78',source['image_sha256']],
 'review':'Current first-page double-chevron at672,645; background128,72 blank; original672,488.88 gap not a button. True empty-results source visibly names unique control query and displays search form;404 is the native empty-results response. Blank source truly blank. History index41 states a plan to check page5, not exhaustive inspection. Expectations frozen before UI replies.',
 'limits':['No positive explicit visible-loading indicator source; blank permits possible loading only.','Old alignment controls replay a frozen recorded point reading; not an end-to-end UI point/alignment success.','All controls are nonblind development selection on limited sources, not general accuracy or Mirage-rate estimates.'],
 'private_expectations_never_sent_to_checker':True,'ready_for_isolated_real_model_preflight_only':True,'formal_trial_ready':False}
(dest/'PRIVATE-independent-review.json').write_text(json.dumps(review,indent=2),encoding='utf8')
manifest={'parent':str(parent),'parent_manifest_sha256':hashlib.sha256((parent/'manifest.json').read_bytes()).hexdigest(),'cases':len(cases),'unique_original_images':review['unique_original_images'],'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.iterdir()if p.is_file()},'no_model_calls_before_expectation_freeze':True,'scope':'Development/preflight only; original formal runs/task parameters/results untouched.'}
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
marker={'folder':str(dest),'manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'cases':len(cases),'original_images':review['unique_original_images'],'status':'independently_reviewed_requires_cpu_extension_before_real_inference'}
(prep/'frozen-controls-current.json').write_text(json.dumps(marker,indent=2),encoding='utf8');print(json.dumps(marker))
