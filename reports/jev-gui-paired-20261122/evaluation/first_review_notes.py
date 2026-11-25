"""Bind the first manual image and reply review to the blinded packet only."""

from pathlib import Path
import re
import time

from collect import HERE, read, save, sha

PACKET='1795492542605790400'

# Reviewed as two exact-input, exact-reply groups. All IDs are opaque packet IDs.
COMPUTERS=(
    'P0b9efd1c4d8caa8','P210157cd05a6b4f','P27ae5e5d6dcc65f','P707aac19a5552e6',
    'P96bc7d8037bd283','Pc5d3864123114f1','Pe67f5aadec89383','Pf138a90ce8095a1',
    'Pfd36c56eb685b8d','Pfe1009ec3ff46c7',
)
BOOKS=(
    'P1d37e499166cf68','P38a4ac88bf06999','P56a227743d70029','P6b30a2d4711b6fe',
    'P70cee0fa955233c','P9b3c7b61bceedce','Pac82d411c025285','Pb3121a1c03d110d',
    'Pb9e80cbdcc98079','Pe7131d015f0cd1c',
)


def main():
    packet=HERE/'review-packets'/PACKET
    seals=read(packet/'seal.json')
    assert sha(packet/'semantic-input.json')==seals['semantic-input.json']
    assert sha(packet/'image-quality-input.json')==seals['image-quality-input.json']
    inbox=read(packet/'semantic-input.json')['packets']
    index=read(HERE/'review-work'/PACKET/'image-number.json')
    assert list(read(packet/'image-quality-input.json')['images'])==list(index.values())
    quality={}
    for i,digest in index.items():
        assert sha(packet/'images'/(digest+'.png'))==digest
        quality[digest]={
            'label':'visually_incomplete' if i=='35' else 'coherent_usable',
            'evidence':('Original 1280×720 shows a lone Publish Ad control and a white field; no readable interface body.'
                        if i=='35' else 'Manually viewed pixels show coherent marketplace content or controls, including readable scrolling/footer views. This label does not establish freshness.')}
    judgements={}

    def take(row,label,evidence,**facets):
        return {'decision':row['decision'],'raw_reply_sha256':row['raw_reply_sha256'],
            'current_image_sha256':row['current_image_sha256'],'semantic_label':label,'evidence':evidence,**facets}

    for example,reason in [
        (COMPUTERS,'The Category dropdown is visible; candidate proposes opening it. The indicated point is inside the dropdown. This is an intended action; no claim that the action already happened.'),
        (BOOKS,'Top-left item image visibly shows a row of six full book spines plus a partial spine. Candidate identifies a row and proposes opening the item, without saying it has exactly four books. Target relevance is uncertain; no definite false visual claim in the text.'),
    ]:
        same=[]
        for alias in example:
            row,=inbox[alias]
            judgements[alias]=[take(row,'no_definite_positive',reason,
                                    uncertain_target_relevance=(example==BOOKS))]
            same.append((tuple(row['body_message_ids_in_order']),row['raw_reply_sha256']))
        assert len(set(same))==1

    # Whole 25-response packet read in order; exact conflicting prose/native pairs
    # are tracked on their own axis. Missing-current-image expectation is qualified.
    trial='P6e3db394ed70dd0'
    cases={
        1:'Category dropdown visible. Candidate proposes selecting Cell phones.',
        2:'No current image. "should now be open" is a qualified expectation based on the prior action; no assertion of a currently observed open menu. Repeated click is a proposed attempt.',
        3:'Closed Category dropdown has a visible blue focus outline on this original.',
        4:'Open list contains Cell phones; proposed point maps into that option.',
        5:'Closed dropdown reads Select a category, supporting selection not taking.',
        6:'Open list shows Cell phones again; no asserted selection before the click.',
        7:'Earlier screenshots establish the list opened and closed without selection. Reply proposes keyboard use next.',
        8:'Open list shows Cell phones and the reply proposes typing to navigate.',
        9:'Highlighted Cell phones and field text support selection; Search button is visible. Native click outcome is not assumed.',
        10:'Category header, total 875 and Newly listed sort are visible; changing sort is a plan.',
        11:'Three visible sort options exclude Oldest first. 875 / 12 implies 73 pages; no claim the current page changed.',
        12:'Maintains earlier sort observation and proposes scrolling for pagination.',
        13:'Top clipped description includes Pink; reply does not infer the phone screen color from that text.',
        14:'Exploratory scroll to find pagination. No definite assertion that an unseen target is present/absent.',
        15:'Footer shows pages 1–3 with next and last-page controls. Proposal is to click the last-page control.',
        16:'Header shows 865–875 of 875 sorted Newly listed. A visible listing has date 2023/10/02.',
        17:'Hot pink phone and $40, date and location are visible. Says scroll up slightly but emits native direction down.',
        18:'Purple/blue screen description uses "appears"; bottom visible listing date is 2023/10/01. Continue scrolling is consistent with native down.',
        19:'Footer highlights 73 and last item date is 2023/10/01; legal prior image shows a pink screen. Says scroll back up but emits native direction down.',
        20:'Visible page bottom and legal earlier pink-screen row. Says scroll up but emits native direction down.',
        21:'Bottom remains visible. Says scroll up twice but emits native direction down.',
        22:'Intends keyboard navigation to top and emits Home; no claim that the current image already changed.',
        23:'Top range and first listing are visible; lower viewport shows Galaxy J7 Prime title. Plans to inspect it.',
        24:'Pink phone and corresponding price/location/date are visible. Prior title grounds the identity.',
        25:'Detail page confirms model name, price, date, location and pink T-Mobile screen. Earliest ranking across every tie is not independently established by that page.',
    }
    assert set(cases)=={t['decision'] for t in inbox[trial]}
    judgements[trial]=[]
    for t in inbox[trial]:
        i=t['decision']
        direction=i in {17,19,20,21}
        if direction:
            assert re.search(r'scroll.{0,7}up',t['raw_reply'],re.IGNORECASE) and '"direction":"down"' in t['raw_reply']
        judgements[trial].append(take(t,'unresolved' if i==25 else 'no_definite_positive',cases[i],
            native_direction_conflict=direction,abnormality_explicitly_recognized=False,
            scope='current_observation_missing' if i==2 else 'legal_current_and_history'))
    dst = HERE/'labels'/str(time.time_ns())
    dst.mkdir(parents=True,exist_ok=False)
    save(dst/'review.json',{'packet_seal_sha256':sha(packet/'seal.json'),'packet_key':PACKET,
        'manual_first_pass_scope':'whole single-response groups plus one complete sequence',
        'quality_labels':quality,'candidate_labels':judgements,
        'reviewer_information':'One reviewer. Arm, executed actions, and official scores excluded from packet. Missing/incomplete imagery is visible and prior design/results were known; no full-blind claim.',
        'known_unreviewed_candidates':sum(map(len,inbox.values()))-sum(map(len,judgements.values())),
        'joined_private_execution_labels':False})
    save(dst/'seal.json',{'review.json':sha(dst/'review.json')})
    print(dst)


if __name__=='__main__':
    main()
