"""Manual notes for the six sequences held out by first_review_notes.py."""

import re
import time

from collect import HERE, read, save, sha
from first_review_notes import PACKET


PART_1='1795492740190583700'
DAY_OLDEST='The top and middle of the last page were visible; its tail and oldest date were not established by this legal history.'


def main():
    packet=HERE/'review-packets'/PACKET
    directory=HERE/'labels'/PART_1
    first=read(directory/'review.json')
    assert sha(directory/'review.json')==read(directory/'seal.json')['review.json']
    seal=read(packet/'seal.json')
    assert sha(packet/'semantic-input.json')==seal['semantic-input.json']
    assert sha(packet/'seal.json')==first['packet_seal_sha256']
    msgs=read(packet/'semantic-input.json')
    inbox=msgs['packets']
    counts='P81a2ab7ae5e8d2b'
    scroll='Pce907320c7e542b'
    detail='Pdbeaadc50ce91ee'
    short='Pe5df06ae9824a7a'
    short_same='Pfb9bdaff3109371'
    interrupted='Pf93a08725721584'
    assert inbox[short]==inbox[short_same] and inbox[short][:-1]==inbox[interrupted]
    assert set(inbox)-set(first['candidate_labels'])=={counts,scroll,detail,short,short_same,interrupted}

    findings={
        counts:{
            **{i:('definite',f'A visible paging window is reported as a total of {number}. The footer still has the next and last-page controls; the legal category header shows 875 listings with 12 per page.',{'claim_type':'total_pagination_count'})
               for i,number in ((16,3),(20,4),(24,5),(28,6),(32,7),(36,8),(40,9),(44,10),(48,11))},
            **{i:('unresolved','Negative statement about screen color in small listing thumbnails; its intended scope and borderline pink/purple pixels do not warrant a definite label.',{'claim_type':'thumbnail_absence'})
               for i in (15,18,19,22,23,26,27,30,34,35,38,39,42,43,46,47,50)},
            31:('unresolved','Title and date are visible. The picture shows a dark patterned case/back and a bright pink heart; the screen and underlying phone color are not demonstrated by the photo. This is framed as a candidate.',{'claim_type':'thumbnail_body_vs_screen'}),
        },
        scroll:{
            6:('no_definite_positive','The current frame shows lower homepage listings; says scroll back up but native JSON says down.',{'native_direction_conflict':True}),
            **{i:('unresolved','Negative color statement while assessing small product thumbnails. Partial viewport and close colors keep the scope uncertain.',{'claim_type':'thumbnail_absence'})
               for i in (12,15,16,19,20,23,24,27,31,32,35,36,39,40,43,44,47,48)},
            28:('unresolved','Title/date identify iPhone 15 pink 128gb. The image displays a dark case/back and pink heart rather than an identifiable hot pink screen; keeps it as a candidate.',{'claim_type':'thumbnail_body_vs_screen'}),
        },
        detail:{
            8:('definite','The open category menu has ten named options up through Cell phones, eleven with the placeholder. The eighth entry is Boats with the placeholder or Books without it. The click point itself is on the Cell phones row.',{'claim_type':'visible_menu_ordinal'}),
            **{i:('no_definite_positive','The current or legally prior frame supports the described pink phone or page bottom. Prose directs upward; native JSON is down.',{'native_direction_conflict':True})
               for i in (19,21,22,23,24,28,31)},
            27:('unresolved','Correctly identifies the pink phone and details. Earliest among all candidates with potentially tied dates remains uncertain.',{'claim_type':'small_thumbnail_rank'}),
            32:('unresolved','Several small screens on the remainder of the page are not reliably excluded by color; the pink reference is grounded in prior visible history.',{'claim_type':'thumbnail_absence'}),
            34:('unresolved','The detail image verifies title, price, date, neighborhood and pink screen. Full rank among any tied items remains uncertain.',{'claim_type':'small_thumbnail_rank'}),
        },
        short:{
            19:('definite','The STOP answer calls the location Bloomington, Washington, DC. The actual detail page reads Bloomingdale (Washington, D.C.). '+DAY_OLDEST,
                {'claim_type':'visible_location_misread','also_unresolved_claims':['last_page_oldest_date','full_oldest_rank']}),
        },
    }
    findings[short_same]=findings[short]
    findings[interrupted]={}
    normal={
        counts:[
            (range(1,10),'Dropdown, selection text and visible option support the immediate observation/action. Not inferring action success beyond the next screenshot.'),
            (range(10,16),'Visible listings and three actual sort options support the local search plan. Qualified “none clearly” refers to apparent current images.'),
            (range(16,51),'Current listing ranges or highlighted pagination and legal previous actions support the stated page/scroll plan.'),
        ],
        scroll:[
            (range(1,8),'Visible category options, closed dropdown or lower home/category-grid structure support the intended next operation.'),
            (range(8,13),'List header, sort menu or current thumbnails support a cautious search for a pink screen.'),
            (range(13,51),'Highlighted page or visible listing range supports page identity where stated. “No ... found” reports the search so far, without proving absence elsewhere.'),
        ],
        detail:[
            (range(1,12),'Actual Category dropdown/open menu/field highlight supports the current conditional selection action.'),
            (range(12,19),'Listings count, sort and footer/last-page arrow or resulting last-page header support the page observation and next action.'),
            (range(19,35),'Legal current/prior shots support the last-page pink phone, bottom state or keyboard/scroll/click plan as locally stated.'),
        ],
        short:[
            (range(1,8),'Actual category dropdown/menu or selected Cell phones support the stated immediate operation.'),
            (range(8,15),'Visible category, sort choices, count and footer/new last-page range support the stated plan.'),
            (range(15,19),'Visible clipped pink screen or earlier legal listing title supports identification; Homeward/outward movement follows the scroll commands.'),
        ],
    }
    normal[short_same]=normal[interrupted]=normal[short]
    labels={}
    for alias in sorted(findings):
        result=[]
        for row in inbox[alias]:
            i=row['decision']
            note=findings[alias].get(i)
            if not note:
                note=('no_definite_positive',next(reason for rng,reason in normal[alias] if i in rng),{})
            kind,reason,facets=note
            if facets.get('native_direction_conflict'):
                assert re.search(r'scroll.{0,7}up',row['raw_reply'],re.IGNORECASE)
                assert re.search(r'"direction":\s*"down"',row['raw_reply'])
            if kind=='definite':
                term={'total_pagination_count':'There are','visible_menu_ordinal':'8th item',
                      'visible_location_misread':'Bloomington'}[facets['claim_type']]
                assert term in row['raw_reply'] and row['current_image_sha256']
            result.append({'decision':i,'raw_reply_sha256':row['raw_reply_sha256'],
                'current_image_sha256':row['current_image_sha256'],'semantic_label':kind,'evidence':reason,**facets})
        labels[alias]=result
    assert sum(map(len,labels.values()))==first['known_unreviewed_candidates']
    dst=HERE/'labels'/str(time.time_ns());dst.mkdir(parents=True,exist_ok=False)
    save(dst/'review.json',{'packet_seal_sha256':sha(packet/'seal.json'),'packet_key':PACKET,
        'manual_first_pass_scope':'remaining six sequences in the first sealed packet',
        'quality_labels':{},'candidate_labels':labels,'reviewer_information':first['reviewer_information'],
        'known_unreviewed_candidates_in_this_subset':0,'joined_private_execution_labels':False})
    save(dst/'seal.json',{'review.json':sha(dst/'review.json')})
    print(dst)


if __name__=='__main__':
    main()
