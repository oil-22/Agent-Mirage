"""Conservative scope rejection, not a history-truth classifier or output rewriter."""
import re

NOUN=r'(?:search|query|click|navigation|inspection|operation|action|submission)'
VERB=r'(?:executed|performed|completed|submitted|issued|done|started)'
PATTERNS=[
 re.compile(r'\b'+NOUN+r'\b[^.!?;]{0,70}\b(?:has|have|had|was|were)\s+(?:(?:not|never)\s+)?(?:been\s+)?'+VERB+r'\b',re.I),
 re.compile(r'\bno\s+[^.!?;]{0,40}\b'+NOUN+r'\b[^.!?;]{0,35}\b'+VERB+r'\b',re.I),
 re.compile(r'\b(?:never|not\s+yet)\s+(?:searched|clicked|inspected|navigated|submitted)\b',re.I),
]
QUALIFIED=re.compile(r'\b(?:cannot|can\s+not|can[’\x27]t|could\s+not|unable\s+to|unclear|unknown|uncertain|whether|if|may|might|hypothes\w*)\b|\bno\s+(?:evidence|indication|confirmation)\b|\bnot\s+(?:established|confirmed|known)\b',re.I)

def check_current_only_history(value):
    """Reject narrow definite execution assertions in scene/focus reads with no history.

    The caller must establish that this is a CURRENT-ONLY auxiliary projection.
    Full-history candidate verification must not use this rule. Unflagged is not approval.
    """
    errors=[]
    def walk(x,path=''):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,path+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+'[%d]'%i)
        elif isinstance(x,str)and any(path=='.'+k or path.startswith('.'+k+'[')for k in ['visible','limitations','reason']):
            for sentence in re.split(r'(?<=[.!?;])\s+',x):
                if QUALIFIED.search(sentence)or any(q in sentence for q in ['"','“','”']):continue
                for pattern in PATTERNS:
                    match=pattern.search(sentence)
                    if match:
                        errors.append({'path':path,'span':match.group(0),'scope_error':'definite execution-history assertion in current-only auxiliary read'})
                        break
    walk(value)
    return {'reject':bool(errors),'errors':errors,'scope':'narrow source-eligibility check for current-only auxiliary readers, not a historical truth or semantic accuracy classifier','value_modified':False,'opposite_fact_supplied':False,'unflagged_is_not_approval':True}

RETRY_SCOPE='''This auxiliary read has only the current scene, without the earlier execution record.
Your previous raw reply asserted a definite execution-history premise beyond that source scope.
Do not replace it with the opposite event or force a visual/status label. Re-read the SAME
unchanged image and report current visible features; retain appropriate uncertainty about
earlier events. No action, missing GUI fact, target or hidden history is supplied by this check.'''

HISTORICAL_TIME=re.compile(r'\b(?:ever|never|earlier|previously|already|before|prior)\b',re.I)
EVENT_WORD=re.compile(r'\b(?:performed|executed|completed|searched|inspected|navigated|submitted|contained|showed)\b',re.I)
def check_historical_event_sources(value,view):
    """Conservatively withhold determinate past-event claims cited only to CURRENT pixels.

    An earlier image/message is eligible provenance, not automatic truth. This narrow
    supplemental source policy may withhold legitimate current-screen history displays;
    no general history accuracy/release claim. The original verdict is never relabelled.
    """
    errors=[]
    for i,claim in enumerate(value.get('claims',[])):
        text=claim.get('text','')
        if claim.get('kind')not in {'gui_fact','history_report'}or claim.get('status')not in {'supported','contradicted'}:continue
        if not HISTORICAL_TIME.search(text)or not EVENT_WORD.search(text):continue
        eligible=[]
        for ev in claim.get('evidence',[]):
            if 'image_index'in ev and 0<=ev['image_index']<len(view.images)and view.images[ev['image_index']].role=='reference':eligible.append('earlier supplied reference image')
            if 'message_index'in ev and 0<=ev['message_index']<len(view.messages):
                m=view.messages[ev['message_index']]
                if m.get('role')=='assistant':eligible.append('earlier assistant report, not execution proof')
        if not eligible:errors.append({'path':'.claims[%d]'%i,'claim_id':claim.get('id'),'scope_error':'determinate historical-event proposition has no eligible earlier source; current appearance alone is not event chronology'})
    return {'reject':bool(errors),'errors':errors,'value_modified':False,'opposite_fact_supplied':False,'scope':'narrow conservative historical-source eligibility only; eligible or unflagged never means semantically approved'}
