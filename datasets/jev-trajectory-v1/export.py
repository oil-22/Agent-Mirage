"""Build ordered image / native question / YES-NO rows; keep audit fields out of the prompt."""
import ast
from collections import Counter,defaultdict
import hashlib,json,math,sys
from pathlib import Path
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'reports/jev-verifier-finetune-starter-20261125'))
from temporal_head import heldout_images, PROMPT, PROMPT_SHA, REV
from temporal_request import STATE, INSTRUCTIONS, CRITERIA, QUESTION_ID, action_json
BASE=ROOT/'reports/jev-defense-scale-20261122/flash-native-audit-source'
ENC=BASE/'source/src/pplx_decider/protocol.py'
SPLITS=('train','val','test')
def read(p):return json.loads(Path(p).read_bytes())
def rows(p):return [json.loads(b) for b in Path(p).read_bytes().splitlines() if b.strip()]
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(o):return json.dumps(o,ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False).encode()
def write_json(n,x):(HERE/n).write_bytes((json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def write_rows(n,rs):
    with (HERE/n).open('wb') as f:
        for r in rs:f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode())
def getconst(mod,k):
    return next(ast.literal_eval(n.value) for n in mod.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==k for t in n.targets))
def prompt(action):
    a=action_json(action)
    if '<|' in a or '|>' in a:raise ValueError('Action contains special tokens')
    return 'State:\n'+STATE+'\nDispatched native action (JSON): '+a+'\n\nQuestion 0:\n'+INSTRUCTIONS+'\nOptions:\nA: YES: '+CRITERIA['YES']+'\nB: NO: '+CRITERIA['NO']+'\n<|fim_suffix|>'
REASONS={
    'ready':'The archived outcome audit records a visible result at the targeted control.',
    'early':'The archived capture shows the target in its pre-action state before the visible result.',
    'white':'An actual white intermediate browser render obscures the result.',
    'buttons':'An actual fragmentary render shows controls without the requested result.',
    'target_unchanged':'The target did not visibly change; adjacent or unrelated UI is not its outcome.',
    'boundary':'An unchanged boundary case was reserved; it was not treated as a negative.',
    'ambiguous':'The archived review does not establish the outcome.'
}
def gui_reviews():
    k=read(HERE/'gui-review-index.json'); review=read(HERE/'gui-review.json'); proof=read(HERE/'scroll-proof.json')
    assert sha(canon(k))==review['index_canonical_sha256']
    assert {k[c] for c in review['pixel_corroboration'].split()}==set(proof)
    out={}
    for label,reason,codes in review['decisions']:
        for code in codes.split():
            assert k[code] not in out
            out[k[code]]=(label,reason,code)
    for c,v in k.items():
        if v not in out:
            assert c.startswith('S')
            out[v]=(*review['remaining_scroll_decision'],c)
    return out
def oid(r):return sha(canon([r['suite'],r['run'],r['event'],r['capture_id'],r['pair_id']]))
def part(r):return r.get('assigned_split') or ('train' if r['suite']=='guard' and r['family']=='atelier' else {'scale':'train','gui':'train','guard':'val','outcome':'test'}[r['suite']])
def family(r):return r.get('family_key',r['family'])
def task(r):return r.get('task_key',family(r)+':'+r['task'])
def split_groups(r):return [('family',family(r)),('task',task(r)),('trajectory',r['suite']+':'+r['run']),('event',r['suite']+':'+r['event']),('capture',r['capture_id']),('capture',r['before_capture_id'])]
def generate():
    encmod=ast.parse(ENC.read_bytes()); system=getconst(encmod,'SYSTEM_PROMPT')
    assert read(BASE/'decision_config.json')['codes'][:2]==['A','B'] and getconst(encmod,'MARKER')=='<|fim_suffix|>'
    write_json('protocol.json',dict(model='Jev / pplx_decider',checkpoint_revision=REV,system_prompt=system,question_id=QUESTION_ID,image_order=['previous_accepted_full_screenshot','current_candidate_full_screenshot'],user_text=prompt({'type':'back'}).replace(action_json({'type':'back'}),'{canonical_action_json}'),answer_codes={'A':'YES','B':'NO'},prompt_builder_sha256=PROMPT_SHA,encoder_sha256=sha(ENC.read_bytes()),decision_config_sha256=sha((BASE/'decision_config.json').read_bytes()),note='prompt is the complete native user text block after both images; global system text is stored once here. For the native API use state/questions, do not paste this block into state a second time.'))
    obs=rows(HERE/'observations.jsonl')
    for f in sorted(HERE.glob('additional-*-observations.jsonl')):obs.extend(rows(f))
    by=defaultdict(list); reviews=gui_reviews(); protect=heldout_images(); reserved=[]; pending=[]; accepted=[]; used=set()
    ai=HERE/'archive-content-index.json'; identity=read(ai) if ai.exists() else {}
    def screen(h):
        if h not in identity:
            with Image.open(HERE/'images'/(h+'.png')) as im:
                w,hh=im.size;rgb=im.convert('RGB')
                # Web sources are landscape; Android has a separate UI-body digest.
                identity[h]=[sha(canon([w,hh])+rgb.tobytes()),w,hh]
        return identity[h]
    prot_core={screen(h)[0] for h in protect if (HERE/'images'/(h+'.png')).is_file()}
    for o in obs:
        pid=o['pair_id']; assert pid==sha(canon([o['before_sha256'],o['action'],o['candidate_sha256']]))
        i=oid(o);assert i not in used,i;used.add(i);by[pid].append(o)
    for pid,g in sorted(by.items()):
        r=g[0]; ids=[oid(o) for o in g]
        info=dict(pair_id=pid,images=['images/'+r['before_sha256']+'.png','images/'+r['candidate_sha256']+'.png'],action=r['action'],observation_ids=ids,source_suites=sorted({o['suite'] for o in g}))
        if protect.intersection([r['before_sha256'],r['candidate_sha256']]) or prot_core.intersection({screen(r[k])[0] for k in ('before_sha256','candidate_sha256')}):
            reserved.append(dict(**info,reason='Shares an image with the frozen regression reference.'));continue
        if len({part(o) for o in g})!=1:
            pending.append(dict(**info,reason='The same input belongs to multiple assigned split groups.'));continue
        labs=set();ev=[]
        for o in g:
            if o['suite']=='gui':l,why,code=reviews[pid]
            else:l,why,code=o['label'],o.get('reason') or REASONS.get(o['truth'],o['truth']),None
            if l is not None:labs.add(l);ev.append((o,why,code))
        if len(labs)>1: # don't resolve contradictory independent labels by majority.
            pending.append(dict(**info,reason='Conflicting definite sources.'));continue
        if not ev:pending.append(dict(**info,reason=why,review_code=code));continue
        selected,reason,code=sorted(ev,key=lambda v:(v[0]['suite'].startswith('archive'),v[0]['suite']=='gui',bool(v[0].get('visual_override')) is False,v[0]['run'],v[0]['capture_id']))[0]
        label,=labs
        phase='settled' if selected['suite']=='gui' else selected['phase']
        accepted.append((selected,label,phase,reason,code,g,pid))
    # Same PNG pixels / timestamps in Android's system strips / coordinate
    # serialization do not make new training examples. Retain an actual original.
    kept=[];near=defaultdict(list); content_splits={}; alias_conflicts=set();nmerged=0
    def action_equiv(a,b,w,h):
        return a['type']==b['type'] and (math.hypot(w*(a['x']-b['x'])/1000,h*(a['y']-b['y'])/1000)<=6 if a['type']=='click' else a==b)
    def hold(o,k,g,reason):
        pending.append(dict(pair_id=k,images=['images/'+o[q]+'.png' for q in ('before_sha256','candidate_sha256')],action=o['action'],observation_ids=[oid(z) for z in g],source_suites=sorted({z['suite'] for z in g}),reason=reason))
    collisions=defaultdict(list)
    for item in accepted:
        o,l,_,_,_,g,k=item;x,w,h=screen(o['before_sha256']);y=screen(o['candidate_sha256'])[0]
        group=collisions[x,y,o['action']['type']]
        for label,act,pairid in group:
            if l!=label and action_equiv(o['action'],act,w,h):alias_conflicts.update((k,pairid))
        group.append((l,o['action'],k))
    for item in sorted(accepted,key=lambda it:(it[0]['suite'].startswith('archive'),it[-1])):
        o,l,ph,why,code,g,k=item; x,w,h=screen(o['before_sha256']);y=screen(o['candidate_sha256'])[0];s=part(o)
        if k in alias_conflicts:hold(o,k,g,'Equivalent visual inputs carry incompatible definite labels.');continue
        if any(content_splits.get(z,s)!=s for z in (x,y)):
            hold(o,k,g,'Shared rendered screenshot across assigned splits; not used for supervision.');continue
        bucket=(x,y,s,l,o['action']['type']);dup=None
        for prev in near[bucket]:
            if action_equiv(o['action'],prev[0]['action'],w,h):dup=prev;break
        if dup is not None:dup[5].extend(g);nmerged+=1
        else:
            item=(*item[:5],list(g),k);kept.append(item);near[bucket].append(item)
            content_splits[x]=content_splits[y]=s
    manifest=[];views=defaultdict(list); group_split={}; pics={}; audit=[]; pixels={}
    for o,l,ph,why,code,g,k in kept:
        split=part(o)
        for z in g:
            for tag,val in split_groups(z):assert group_split.setdefault((tag,val),split)==split,(tag,val,split)
        for h in (o['before_sha256'],o['candidate_sha256']):
            if h not in pixels:
                p=HERE/'images'/(h+'.png'); assert sha(p.read_bytes())==h
                with Image.open(p) as im:
                    assert im.format=='PNG' and im.n_frames==1
                    pixels[h]=sha(canon(list(im.size))+im.convert('RGB').tobytes())
            assert pics.setdefault(pixels[h],split)==split,'same rendered screenshot across splits'
        ims=['images/'+o[k]+'.png' for k in ('before_sha256','candidate_sha256')]
        sid='jev-'+k[:24]
        m=dict(sample_id=sid,split=split,family_id=family(o),task_id=task(o),trajectory_id=o['suite']+':'+o['run'],event_id=o['suite']+':'+o['event'],capture_id=o['capture_id'],before_png=ims[0],before_sha256=o['before_sha256'],action=o['action'],candidate_png=ims[1],candidate_sha256=o['candidate_sha256'],receipt_valid=True,phase=ph,label=l,reason=why,source_suite=o['suite'],evidence_kind=o.get('evidence_kind','sealed_browser_and_visual_reading' if o['suite']=='gui' else 'signed_controlled_capture_and_independent_outcome_audit'),review_code=code,source_observation_id=oid(o),supporting_pair_ids=sorted({z['pair_id'] for z in g}),all_observation_ids=sorted(oid(z) for z in g))
        manifest.append(m);views[split].append(dict(images=ims,prompt=prompt(o['action']),label=l))
    for split in SPLITS:write_rows(split+'.jsonl',views[split])
    write_rows('manifest.jsonl',manifest);write_rows('pending.jsonl',pending);write_rows('protected.jsonl',reserved)
    write_rows('observation-index.jsonl',[dict(observation_id=oid(z),pair_id=z['pair_id'],suite=z['suite'],run=z['run'],event=z['event'],capture_id=z['capture_id']) for z in obs])
    stats=dict(reference_target=3000,hard_minimum=False,total=len(manifest),splits={s:dict(Counter(v['label'] for v in vals)) for s,vals in views.items()},by_suite={s:dict(Counter(v['label'] for v in manifest if v['source_suite']==s)) for s in sorted({v['source_suite'] for v in manifest})},by_evidence=dict(Counter(r['evidence_kind'] for r in manifest)),supervised_images=len(pixels),pending_unique=len(pending),regression_protected=len(reserved),unique_candidates=len(by),raw_occurrences=len(obs),visual_or_click_aliases_merged=nmerged)
    assert len(manifest)+nmerged+len(pending)+len(reserved)==len(by)
    write_json('stats.json',stats);print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':generate()
