"""Prepare model-blind original PNG sheets and join only explicit visual readings."""

import argparse
from pathlib import Path

from audit_panel import chain, shape_and_interim, verify_frames
from audit_toggle import verify_origin, verify_seal
from audit_truth import classify
from live_common import load, save, sha
from visual_audit import prepare


def preflight(root, evidence):
    manifest,_=verify_seal(root)
    assert manifest['mode']=='capture-preflight'
    origin=verify_origin(root);plan=load(root/'live_plan.json')
    items=[]
    for t in load(root/'run'/'terminal.json')['completed']:
        case=t['case']; folder=root/'run'/'episodes'/case['id']; src=root/'run'/'source'/case['id']
        action=load(src/'action.json'); head,ev=chain(folder/'events.jsonl');term=load(folder/'terminal.json')
        assert head==term['journal_head']
        f,_,_=verify_frames(folder,src,case,ev,{**term,'native_action':action['native_action'],'subsequent_action_executed':False},
                            origin,plan['viewport'],classify=classify)
        items.append({'id':case['id'],'case':case,'frames':list(f.values())})
    save(evidence,{'attempt':root.as_posix(),'episodes':items,'source_seal_sha256':sha(root/'local-seal.json')})


def expected(snapshot):
    target={None:'ordinary_refresh','true':'on','false':'off'}[snapshot['target_state']]
    status={'System status: Idle':'idle','System status: Synced':'synced','Summary refreshed successfully':'refreshed'}[snapshot['elsewhere_text']]
    neighbor={None:None,'Maintenance updates: Off':'off','Maintenance updates: On':'on'}[snapshot['neighbor_text']]
    return target, status, neighbor, snapshot['local_message']


def bind(audit,directory,observations,out):
    p=directory/'raw-review-index.json'; index=load(p); records=load(observations)
    a=load(audit); root=Path(a['attempt'])
    assert sha(audit)==index['audit_sha256'] and records['index_sha256']==sha(p)
    assert all(sha(f['path'])==f['sha256'] for f in index['contact_sheets'])
    reads={r['sha256']:r for r in records['observations']}
    assert len(reads)==len(records['observations']) and set(reads)=={x['sha256'] for x in index['originals']}
    frame_index={(r['id'],f['capture_id']):(r,f) for r in a['episodes'] for f in r['frames']}
    issues=[]; straddles=[]; deliveries={}; hits=0
    unique_excludes=set()
    for x in index['originals']:
        assert sha(x['path'])==x['sha256']
        v=reads[x['sha256']]
        assert v['index']==x['index']
        assert v['target'] in ('on','off','ordinary_refresh','unclear')
        assert v['status'] in ('idle','synced','refreshed','unclear')
        assert v['neighbor'] in (None,'on','off','unclear') and isinstance(v['local_message'],str)
        observed=tuple(v[k] for k in ('target','status','neighbor','local_message'))
        for item in x['uses']:
            episode,f=frame_index[item['episode'],item['capture_id']]
            assert f['source_sha256']==x['sha256'] and item['truth']==f['truth']
            src=load(root/'run/source'/item['episode']/f"capture-{f['capture_index']:03}.json")
            before,after=expected(src['before']),expected(src['after'])
            delivered=bool(episode.get('delivery') and episode['delivery']['capture_id']==item['capture_id'])
            if f['truth']=='ambiguous':
                straddles.append({**item,'sha256':x['sha256'],'equals_visible_before':observed==before,
                                  'equals_visible_after':observed==after,'delivered':delivered})
                continue
            hits+=1
            confirmed=observed==before==after
            if not confirmed:
                issues.append({**item,'sha256':x['sha256'],'visual':observed,'source':[before,after]});unique_excludes.add(x['sha256'])
            if delivered:
                deliveries[item['episode']]=confirmed
    receipt={'source_audit_sha256':sha(audit),'sha_index':sha(p),'observations_sha256':sha(observations),
             'reviewed_unique_pngs':len(reads),'checked_unambiguous_uses':hits,'possible_review_mismatches':issues,
             'mismatching_unique_pngs':sorted(unique_excludes),'straddling':straddles,'bound_deliveries':deliveries,
             'verified_deliveries':sum(deliveries.values())}
    save(out,receipt)
    print(len(reads),'unique original PNGs;',hits,'stable uses;',len(straddles),'crossed render;',len(issues),'mismatches;',sum(deliveries.values()),'deliveries')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('directory',type=Path)
    ap.add_argument('--capture-preflight',action='store_true');ap.add_argument('--observations',type=Path);ap.add_argument('--out',type=Path)
    a=ap.parse_args();d=a.directory.resolve();f=a.input.resolve()
    assert bool(a.observations)==bool(a.out)
    if a.capture_preflight:
        p=d.with_suffix('.json');preflight(f,p);f=p
    if a.observations:
        bind(f,d,a.observations,a.out)
    else:
        prepare(f,d)
