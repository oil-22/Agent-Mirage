"""Freeze original public requests and independent scoped expectations before UI replies."""
import hashlib,json,time,shutil
from pathlib import Path
base=Path(__file__).resolve().parent
source=Path(json.loads((base/'scroll-validation-outcomes-current.json').read_bytes())['folder'])
evidence=json.loads((source/'evidence.json').read_bytes())
dest=base/'uitars-verifier-preparation'/('frozen-controls-'+str(time.time_ns()));dest.mkdir()
selected=[(0,374,'page5-readiness','usable: coherent result list and pagination; no assertion of task success'),
 (0,389,'footer-readiness','usable for bounded evidence seeking; footer is interpretable, not blank/loading; no target or task success inferred'),
 (1,303,'up-prose-down-native','action must not be supported: prose/native conflict; broad uniqueness claim not independently established'),
 (1,312,'corrected-native-up','up direction is consistent and footer supports returning toward earlier content; no global-minimum truth label'),
 (1,326,'actual-first-page-point','visible pagination« at actual current pixel; strict containment and target matching remain required'),
 (1,381,'long-history-candidate','capacity/serialization control only, semantic verdict not preassigned'),
 (1,385,'long-history-completion','capacity/serialization control only; official score never supplied as checker evidence')]
requests=[];expectations=[];images=set()
for ri,seq,name,expected in selected:
 row=evidence['rows'][ri];event=next(e for e in row['late_events']if e['seq']==seq)
 assert event['kind']=='verifier_request'
 requests.append({'id':name,'source_attempt':row['attempt'],'source_event_sha256':event['sha256'],'source_seq':seq,'request':event['data']})
 expectations.append({'id':name,'expectation':expected,'review_basis':'Actual original page5/footer/detail images and legal candidate text, independent of old verifier labels; scoped expectations only'})
 images.update(im['sha256']for im in event['data']['public']['images'])
for sha in images:
 p=source/(sha+'.png');assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
 shutil.copyfile(p,dest/(sha+'.png'))
(dest/'public-requests.json').write_text(json.dumps(requests,ensure_ascii=False,indent=2),encoding='utf8')
(dest/'PRIVATE-review-expectations.json').write_text(json.dumps(expectations,ensure_ascii=False,indent=2),encoding='utf8')
manifest={'created':time.time(),'cases':len(requests),'unique_original_images':len(images),'source_evidence_sha256':hashlib.sha256((source/'evidence.json').read_bytes()).hexdigest(),
 'original_request_data_unchanged':True,'model_inference_calls':0,'ready_for_formal_trials':False,
 'separation':'Only public-requests and original PNGs enter checker serialization; PRIVATE expectations are evaluation-only.',
 'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.iterdir()if p.is_file()}}
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
marker={'folder':str(dest),'manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'cases':len(requests),'original_images':len(images),'status':'frozen_not_inferred'}
(base/'uitars-verifier-preparation/frozen-controls-current.json').write_text(json.dumps(marker,indent=2),encoding='utf8')
print(json.dumps(marker))
