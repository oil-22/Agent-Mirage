"""Freeze the accepted label evidence with its original run and retain unlabelled pairs for review."""
from collections import Counter
import json,os
from archive_files import HERE,WORK
from screen_evidence import paths
from export import canon,read,rows,sha,write_json,write_rows

def numbers(s):
    for z in s.split():
        a,*b=map(int,z.split('-'));yield from range(a,(b[0] if b else a)+1)
def main():
    D=WORK/'archive-review'; rule=read(WORK/'derived-labels.json'); focus=read(WORK/'field-borders.json')
    manual=read(HERE/'archive-review-decisions.json'); audit={s:read(D/(s+'-index.json')) for s in ('N','P','Q')}
    assert [sha(canon(audit[s])) for s in ('N','P','Q')]==[manual[k] for k in ('index_sha256','change_index_sha256','spot_check_index_sha256')]
    write_json('archive-review-index.json',audit)
    for k,ev in focus.items():
        rule.setdefault(k,['YES','visible_focus_ring','A new colored four-sided focus outline surrounds the clicked field, with unchanged interior content.',ev])
    for s,aa in [('N','decisions'),('P','change_decisions')]:
        for l,why,ids in manual[aa]:
            for i in numbers(ids):
                code=s+str(i).zfill(4 if s=='N' else 3);k=audit[s][code]
                assert k not in rule or rule[k][0]==l
                rule.setdefault(k,[l,'visually_supported_noop' if s=='N' and l=='YES' else 'paired_visual_reading',why,{'review_id':code}])
    reps={r['pair_id']:r for r in rows(WORK/'archive-pair-reps.jsonl')}
    for k in list(rule):
        r=reps[k]
        if r['suite']=='archive_vwa' and rule[k][1]=='rendered_navigation' and r['actual_surfaces']!=[r['family']]*2:
            del rule[k]
    # An image audited for a different site is not an independent instance of this task family.
    excluded=[];out=[];digest_by_pair={}; observed=set()
    for r in rows(WORK/'archive-joined.jsonl'):
        web=r['suite']=='archive_vwa';k=r['pair_id']
        if web and r['actual_surfaces']!=[r['family']]*2:
            excluded.append({'pair_id':k,'run':r['run'],'step':r['step'],'source_run':r['source_run'],'reason':'The actual website differs from the archived task family.'});continue
        tag=r['assigned_split']='train' if r['family']=='classifieds' else 'test' if r['family']=='reddit' else 'val'
        lab,kind,why,pf=rule.get(k,[None,'unestablished','The visible outcome has not been established by a selected evidence rule or review.',{}])
        r.update(label=lab,phase='no_change' if kind=='visually_supported_noop' else 'settled' if lab=='YES' else 'unrelated' if lab=='NO' else 'unknown',
                 truth=kind,reason=why,evidence_kind=kind)
        if lab:
            r['evidence_id']=k;observed.add(k)
        out.append(r)
    write_rows('archive-label-evidence.jsonl',[dict(pair_id=k,label=rule[k][0],method=rule[k][1],reason=rule[k][2],evidence=rule[k][3]) for k in sorted(observed)])
    write_rows('additional-archive-observations.jsonl',out);write_rows('archive-source-exclusions.jsonl',excluded)
    for h,p in paths().items():
        dest=HERE/'images'/(h+'.png')
        if not dest.exists():
            # Copy from the verified byte store, independent of temporary working files.
            import shutil
            shutil.copyfile(p,dest)
        assert sha(dest.read_bytes())==h
    # The native screenshot size and a decoded UI-body hash allow the final export
    # to collapse PNG re-encodings and Android status-clock-only differences.
    write_json('archive-content-index.json',read(WORK/'content-sha.json'))
    print('eligible observations',len(out),'site mismatch exclusions',len(excluded),'candidate-level labels:',dict(Counter(rule[k][0] for k in observed)))
if __name__=='__main__':main()
