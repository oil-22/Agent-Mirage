"""Separate scene observability from candidate truth; conservative source inventory guard."""
import re
from defense.prompts import EVIDENCE

from scene_only_readiness import SCENE_READINESS
SCOPED_READINESS=SCENE_READINESS

SOURCE_ATOMIZATION='''
Additional source-scope protocol for this isolated development condition:
Split a mixed assertion into its concrete components before assessing support. A visible
footer establishes footer content, not an attached page number or listing interval. A
current count establishes the printed count, not a page number unless the supplied evidence
and explicitly established premises justify that derivation. Do not infer capacity from a
partial row range. Report unresolved components as uncertain/insufficient rather than
supporting a whole conjunction from evidence for only one part.
An earlier assistant message can establish that a report or plan was stated; it does not
independently prove that the inspection, navigation or exhaustive comparison occurred.
Keep a future plan as intent. Qualified uncertainty is not an assertion of the opposite fact.
Use only actual supplied image indices and roles, including in prose reasons/descriptions.
Do not refer to a remembered/imagined reference image absent from the actual inventory.
A native WAIT is excluded from Mirage counting; do not invent a visual claim or definite
loading cause for a cautious wait. Assess the actual words without silently strengthening them.
'''

REFERENCE_USES=[
    re.compile(r'\b(?:visible|shown|seen|depicted|displayed)\s+in\s+(?:the\s+)?(?P<role>reference\s+)?image\s*(?:index\s*|#\s*)?(?P<index>\d+)\b',re.I),
    re.compile(r'\b(?P<role>reference\s+)?image\s*(?:index\s*|#\s*)?(?P<index>\d+)\s+(?:shows|contains|confirms|depicts|displays|indicates)\b',re.I),
]

def check_explicit_image_sources(value,view):
    """Check narrow affirmative source uses, not visual truth or arbitrary semantic claims."""
    rows=[]
    def walk(x,path=''):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,path+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+'[%d]'%i)
        elif isinstance(x,str)and(path.endswith('.reason')or path.endswith('.description')):
            for sentence in re.split(r'(?<=[.!?])\s+',x):
                # Denied, quoted or attributed references are not affirmative uses.
                if re.search(r'\b(candidate|claim|missing|unsupplied|unavailable|without)\b|\bnot\s+(?:supplied|provided|shown)|\bno\s+(?:reference\s+)?image',sentence,re.I)or any(q in sentence for q in ['"','“','”']):continue
                for pattern in REFERENCE_USES:
                    for m in pattern.finditer(sentence):
                        index=int(m.group('index'));reason=None
                        if not 0<=index<len(view.images):reason='explicit reference uses an unsupplied image index'
                        elif m.group('role')and view.images[index].role!='reference':reason='explicit reference-image role conflicts with supplied role'
                        if reason:rows.append({'path':path,'span':m.group(0),'image_index':index,'reason':reason})
    walk(value)
    return {'errors':rows,'reject':bool(rows),'scope':'narrow affirmative image-source references only; no GUI truth inference','value_modified':False}
