"""Reuse a review only for identical complete legal messages, current pixels and raw reply."""

import argparse
import json
from pathlib import Path
import time

from collect import HERE, read, save, sha
from extract_on_host import canonical, hx
from link import verify


def load_packet(path):
    seal=read(path/'seal.json')
    for k in ('semantic-input.json','image-quality-input.json'):
        assert sha(path/k)==seal[k]
    value=read(path/'semantic-input.json')
    assert all(hx(canonical(m))==d for d,m in value['messages'].items())
    return value,seal


def signature(turn):
    assert hx(turn['raw_reply'].encode())==turn['raw_reply_sha256']
    return (tuple(turn['body_message_ids_in_order']),turn['current_image_sha256'],
            turn['raw_reply_sha256'],turn['raw_reply'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet',type=Path)
    parser.add_argument('previous_labels',type=Path,nargs='+')
    args=parser.parse_args()
    target,seal=load_packet(args.packet)
    searchable={}; clashes=set(); audited={}
    sources=[]
    for folder in args.previous_labels:
        verify(folder)
        prior=read(folder/'review.json')
        p=HERE/'review-packets'/prior['packet_key']
        assert prior['packet_seal_sha256']==sha(p/'seal.json')
        inbox,_=load_packet(p)
        for alias,judgements in prior['candidate_labels'].items():
            turn_by_id={x['decision']:x for x in inbox['packets'][alias]}
            for v in judgements:
                candidate=turn_by_id[v['decision']]
                assert candidate['raw_reply_sha256']==v['raw_reply_sha256']
                assert candidate['current_image_sha256']==v['current_image_sha256']
                k=signature(candidate)
                old=searchable.setdefault(k,(prior['packet_key'],alias,v))[-1]
                if any(old.get(attr)!=v.get(attr) for attr in ('semantic_label','native_direction_conflict',
                                                              'also_unresolved_claims','claim_type')):
                    clashes.add(k)
        for d,qual in prior['quality_labels'].items():
            old=audited.setdefault(d,qual)
            assert old['label']==qual['label']
        sources.append(sha(folder/'seal.json'))
    inherited={}; missing=[]; reused_quality={}
    for alias,turns in target['packets'].items():
        for turn in turns:
            k=signature(turn)
            if k not in searchable or k in clashes:
                missing.append([alias,turn['decision']])
                continue
            earlier,source_alias,old=searchable[k]
            inherited.setdefault(alias,[]).append({**old,'decision':turn['decision'],
                'exact_review_reuse_from':{'packets':earlier,'packet_id':source_alias,'decision':old['decision']}})
    for d in read(args.packet/'image-quality-input.json')['images']:
        if d in audited:
            assert sha(args.packet/seal['original_images'][d])==d
            reused_quality[d]=audited[d]
    if not inherited and not reused_quality:
        print(json.dumps({'exact_reused_replies':0,'manual_candidates_remaining':len(missing)}))
        return
    dst=HERE/'labels'/str(time.time_ns());dst.mkdir(parents=True,exist_ok=False)
    save(dst/'review.json',{'packet_key':args.packet.name,'packet_seal_sha256':sha(args.packet/'seal.json'),
        'candidate_labels':inherited,'quality_labels':reused_quality,'exact_source_label_seals':sources,
        'still_requires_manual_candidate_review':missing,'joined_private_execution_labels':False,
        'rule':'Exact ordered legal body message hashes including every historical image, same current image and exact reply text; no approximate or metric-based matching.'})
    save(dst/'seal.json',{'review.json':sha(dst/'review.json')})
    print(json.dumps({'labels':str(dst),'exact_reused_replies':sum(map(len,inherited.values())),
                      'manual_candidates_remaining':len(missing),'exact_reused_images':len(reused_quality)}))


if __name__=='__main__':
    main()
