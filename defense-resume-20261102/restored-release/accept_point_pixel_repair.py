"""Source/image review of development controls; not semantic labels or efficacy."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent;raw=(r/'point-pixel-protocol-development-evidence/summary.json').read_bytes();s=json.loads(raw)
dev=json.loads((r/'v3.9.8-protocol-staging.json').read_bytes())
prior=json.loads((r/'point-pixel-development-evidence/summary.json').read_bytes())
assert not prior['passed']and prior['results'][6]['case']=='older_failure_page_one'and not prior['results'][6]['passed']
assert s['passed']and len(s['results'])==8 and all(v['passed']and 1<=v['verifier_calls']<=2 for v in s['results'])
assert sum(v['verifier_calls']for v in s['results'])==9
assert s['results'][0]['exact_public_and_mechanical_query_unchanged_actual_pixel_projection_logged']
assert s['results'][0]['verdict']['evidence'][0]['box_xyxy']==[838,468,878,508]
assert s['results'][6]['verifier_calls']==2 and s['results'][6]['verdict']['evidence'][0]['box_xyxy']==[655,469,685,511]
review={'allow_online':True,'scope':'Nonblind development acceptance, not independent Mirage labels or efficacy','summary_sha256':hashlib.sha256(raw).hexdigest(),'engineering_tests':126,'real_controls':8,'actual_verifier_calls':9,
'source_review':'Directly viewed both byte-identical original1280x720 failure screenshots. Current point853.76,488.88 lies on page5 between highlighted4 and next. Returned pixels838,468,878,508 match the actual page5 button. Adjacent4 region793,470,832,509 matches the dark4 control. Margin128,72 is background; Contact172.8,630 is actual footer text, region150,620,210,640. Older point669.44,488.88 lies on page1; corrected localized region655,469,685,511 is within that button, not the preceding chevron. No target labels or boxes were given to the reader.',
'repair':'Only independent point-reader protocol uses original pixels, with exact pixel geometry and same unchanged locator. Actual judge payload is logged as sent; original normalized mechanical query is separately logged and sent to unchanged strict validator. Other prompts/validators/native actor/source images/full histories/conditions/budgets unchanged. No auto conversion or invented bbox repair.',
'development_failure_retained':{'preservation':dev['prior_zero_retry_failure_preservation'],'summary_sha256':dev['prior_development_summary_sha256'],'description':'Earlier zero-format-retry development:7/8 controls passed, older image misread preceding chevron and strict containment rejected. Entire attempt/release/logs/hashes preserved. Not hidden or relabeled successful.'},
'full_original_protocol':'Same8 predeclared controls were replayed in new development root using original one-format-retry allowance. Older wrong-neighbor read was again rejected; format retry independently returned visible1 with valid localized pixel evidence. This is9 calls, not8 one-call successes, and does not increase formal budgets.',
'negative_and_wait_controls':'Stated page5 matched frozen5; stated page4 at actual5 contradicted. Pure nativeWAIT retained. Mixed-unit boxes still rejected by strict regression tests.',
'limitations':'Only two nonblind development screenshots and dedicated target/text/WAIT controls. Does not prove general localization accuracy, full two-run task recovery or Mirage reduction. The new full joint trajectory has not yet reached failed step20; online failures/blocks remain possible and must be preserved.',
'resume_policy':'Resume only two unfinished independent scroll validations in linked new attempts. Never restart original completed20, retry terminal blocks or enlarge call/output/step/regeneration/recapture budgets.'}
out=r/'v3.9.8-development-review.json';assert not out.exists();out.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'allow_online':True,'summary_sha256':review['summary_sha256'],'controls':8,'calls':9}))
