"""Conservative labels based on independent logged effects AND visible evidence in the real PNGs."""
from collections import defaultdict,Counter
from urllib.parse import urlsplit,parse_qsl
import json,re
from archive_files import WORK
from export import rows,canon,sha
from read_typed_fields import norm

def getroute(s):
    z=urlsplit(s or '');q=dict(parse_qsl(z.query,keep_blank_values=True));return z.path,tuple(sorted((k,v) for k,v in q.items() if k in {'page','id','sPattern','sCategory','sCity','sRegion','sPriceMin','sPriceMax','iPage','sPage','sOrder','iOrderType','sShowAs','q','sort','pageNumber','next','show','after','before','search','order'}))
def nav(r,v):
    a=r['action'];f=r['family']
    if r['suite']!='archive_vwa' or a['type'] not in ('click','press','back') or (a['type']=='press' and a['key'] not in ('Enter','Return')):return False
    l=getroute(r['before_url_path']);rr=getroute(r['after_url_path'])
    if ('/login' in rr[0] or '/logout' in rr[0] or l==rr or v['tiles']<9 or min(v['coverage'])<3 or v['change']<.035 or min(v['edges'])<.017):return False
    if f=='classifieds':
        return all(p in ('/','/index.php') for p in (l[0],rr[0]))
    if f=='reddit':
        return all(p=='/' or p.startswith(('/f/','/forums','/search','/active','/new','/top','/hot','/user/','/tag/')) for p in (l[0],rr[0]))
    return False
def main():
    rep={r['pair_id']:r for r in rows(WORK/'archive-pair-reps.jsonl')}
    f={r['pair_id']:r for r in rows(WORK/'visual-features.jsonl')};ty={r['pair_id']:r['match'] for r in rows(WORK/'typed-reading.jsonl') if r['match']}
    s=json.loads((WORK/'content-sha.json').read_bytes())
    def core(h):return s[h][0]
    def changed(v):return v['tiles']>=7 and v['change']>.04 and min(v['edges'])>.013
    lab={};by=defaultdict(dict)
    for o in rows(WORK/'archive-joined.jsonl'):
        by[o['run']][o['step']]=o
    for pid,r in rep.items():
        v=f[pid];a=r['action']
        if nav(r,v):
            lab[pid]=['YES','rendered_navigation','A successful native navigation action changed the task-relevant route, and populated content changed across the target page.',dict(before_route=r['before_url_path'],after_route=r['after_url_path'],changed_fraction=v['change'],changed_tiles=v['tiles'])]
        elif a['type']=='scroll' and v.get('scroll_translation'):
            lab[pid]=['YES','directional_scroll','Distinctive separated patches on the same UI translated together in the dispatched scroll direction.',v['scroll_translation']]
        elif a['type']=='type' and pid in ty and len(norm(a['text']))>=3 and v['change']<.045 and v['tiles']<15:
            lab[pid]=['YES','visible_typed_text','In a changed field-sized region, OCR reads the dispatched text in the candidate; it was absent or occurred fewer times in that region before.',ty[pid]]
    for run,steps in sorted(by.items()):
        old={}
        for i,o in sorted(steps.items()):
            pid=o['pair_id'];x=core(o['before_sha256']);y=core(o['candidate_sha256']);a=o['action'];v=f[pid];n=steps.get(i+1)
            if x!=y and changed(v) and pid not in lab:
                if a['type']=='back' and y in old:
                    lab[pid]=['YES','returned_to_previous_view','Back restored the visible UI of an earlier accepted screenshot in this same trajectory.',dict(run=run,step=i,earlier=old[y],restored_content_sha256=y)]
                elif a['type']=='click' and n and n['action']['type']=='back' and n['before_sha256']==o['candidate_sha256'] and core(n['candidate_sha256'])==x:
                    lab[pid]=['YES','click_and_back','The click opened a visibly different view. The immediately following Back restored the exact earlier UI content.',dict(run=run,step=i,inverse=n['pair_id'],restored_content_sha256=x)]
                elif a['type']=='scroll' and n and n['before_sha256']==o['candidate_sha256'] and n['action']['type']=='scroll' and n['action']['direction']!=a['direction'] and core(n['candidate_sha256'])==x and o['before_url_path']==o['after_url_path']:
                    lab[pid]=['YES','reversible_scroll','The viewport changed on the same page and an immediate opposite-direction scroll restored the earlier content.',dict(run=run,step=i,inverse=n['pair_id'],restored_content_sha256=x)]
                    if n['pair_id'] not in lab:
                        lab[n['pair_id']]=['YES','reversible_scroll','Scrolling in the opposite direction restored the exact earlier view of this page.',dict(run=run,step=i+1,inverse=pid,restored_content_sha256=x)]
            old[x]=dict(step=i,image=o['before_sha256'])
    # A stationary viewport alone has no label. An actual visible counterexample
    # at the very same content/coordinate can establish a missing result for that target.
    controls=defaultdict(list)
    for pid,(l,kind,_,_) in sorted(lab.items()):
        r=rep[pid];a=r['action']
        if l=='YES' and a['type'] in ('click','type') and kind in ('rendered_navigation','click_and_back','visible_typed_text'):
            controls[core(r['before_sha256']),canon(a)].append(pid)
    for pid,r in rep.items():
        a=r['action'];x=core(r['before_sha256']);y=core(r['candidate_sha256'])
        if x!=y or pid in lab or a['type'] not in ('click','type'):continue
        choices=controls.get((x,canon(a)))
        if choices:
            lab[pid]=['NO','matched_no_visible_outcome','In an archived positive control, the same action on the same visible starting UI produced a visible result. Here the target remains exactly as before.',dict(actual_positive_control=choices[0],same_content_sha256=x)]
    (WORK/'derived-labels.json').write_bytes(canon(lab))
    print('evidence groups',dict(Counter((q[0]+'/'+q[1]) for q in lab.values())),flush=True)
if __name__=='__main__':main()
