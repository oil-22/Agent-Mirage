"""Current-image scene observability; no task, candidate, action or execution history."""
import json
from dataclasses import replace

SCENE_READINESS='''Assess ONLY the supplied CURRENT screenshot's visual interpretability.
You receive image provenance, not a task, candidate, action history or execution record.
Report features that are visible NOW. Never infer whether a search, click, inspection,
navigation or submission occurred earlier, or whether a task is completed. An empty field
only establishes its present appearance. Do not invent an explanation for missing content.

Return usable if the actual image contains coherent interpretable interface context such
as a form, links, a normal footer, readable empty-results notice or listing fragments.
This certifies only scene interpretability. It does not certify an action, focus, target,
page identity, coverage, minimum, success or prior execution. Offscreen content is unknown.
Return limited for blank/absent/undecodable content, visible unfinished transition or
uninterpretable fragments. Return unknown if you cannot decide. Do not force usable.
An empty image does not establish no-results or completion. Only an actual visible
loading indicator establishes loading:visible; otherwise use not_observed or uncertain.

Return one compact raw JSON object with original mandatory fields:
{"status":"usable|limited|unknown","visible":["brief current feature"],"limitations":[],
"loading":"visible|not_observed|uncertain","evidence":[IMAGE citation],"reason":"brief visual basis"}.
Use at most three concise visible facts. Limitations describe current readability/occlusion,
not hypothetical task prerequisites or past events. No navigation advice or invented facts.
usable requires evidence from the actual current image. IMAGE citations use actual
observation_id,image_index,coordinate_space,box_xyxy,description. normalized_1000 is0..1000
on BOTH axes; pixels uses original dimensions. Do not invent/clamp boxes or reference images.
No Markdown or extra fields. Every returned statement remains subject to strict validation.
'''

def scene_projection(view):
    images=tuple(im for im in view.images if im.role=='current')
    payload={'current_image_provenance_only':[{'image_index':i,**im.info()}for i,im in enumerate(images)]}
    return replace(view,messages=[{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],
                   images=images,recent_action='',execution_feedback='')
