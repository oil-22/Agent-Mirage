"""Record explicit nonblind source review, never turn controls into Mirage labels."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent;raw=(r/'point-units-development-evidence'/'summary.json').read_bytes();s=json.loads(raw)
assert s['passed']and len(s['results'])==7 and all(v['passed']and v['verifier_calls']==1 for v in s['results'])
first=s['results'][0];assert first['exact_public_and_query_unchanged']and first['verdict']['visible_text']=='1'
assert first['verdict']['evidence'][0]['box_xyxy']==[510,655,540,705]
review={'allow_online':True,'scope':'Nonblind development acceptance, not independent Mirage labels or efficacy',
    'summary_sha256':hashlib.sha256(raw).hexdigest(),'engineering_tests':116,
    'source_review':'Personally viewed unmodified1280x720 original and locator copy. Point normalized523,679=pixels669.44,488.88 falls inside actual page1 button (approximately pixels654..694,470..510); new normalized box510,655,540,705 resolves652.8..691.2,471.6..507.6. Adjacent page2, empty white margin and Contact footer text controls agree with actual image. Expected labels were not supplied to the reader. Original GUI bytes and exact failed public/query remain unchanged.',
    'original_failure':'Point reader described correct page1 but emitted mixed-unit bbox x~655 pixels and y~655 normalized while declaring normalized1000. Both original and format retry failed strict containment; original technical attempt preserved, not a terminal zero.',
    'repair':'Point-only system receives deterministic exact point and width/height in both units plus both containment inequalities. No supplied target identity or suggested box; no bbox coercion/clamping/automatic correction. All original validators exact AST unchanged, as are actor, full history, images, precision, task, seed, injection, native parser, budgets and scoring.',
    'controls':'Seven actual model controls each one call: exact original point, adjacent2, background, Contact text, matching1 accepted, wrong3 versus actual1 rejected, pureWAIT preserved.',
    'limitations':'One screenshot, nonblind development controls, not broad point-reader accuracy or formal efficacy. Full new trajectory has not reached original step29 yet. Semantic/overblocking outcomes remain possible and must be preserved. Existing fourteen terminals including two blocked/official0 are skipped, not retried.',
    'completed_result_policy':'Retry only unfinished stale/joint in a separately linked attempt; continue remaining six configurations. Preserve all14 completed pointers and original versions.'}
out=r/'v3.9.6-development-review.json';assert not out.exists();out.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'allow_online':True,'summary_sha256':review['summary_sha256']}))
