"""Seal source-first observations on the 13-reply packet, without joining execution labels."""

import time

from collect import HERE, read, save, sha
from link import verify


PACKET='1795494518461206600'
EXACT='1795494566764898300'
ALIAS='Pc1c29f225a0b0a0'
BLANK='c4b3344c0140948b69d89b18ffd9f7f3c7517d71415595458dc3a82eb4f89b78'
MENU='c2fae889cf2473a6dc2aab237f8f75fb225b6fbccf3ddf70c22efd6ee0823ba1'


REVIEW={
    2:('pure_native_WAIT_excluded','The current original is uniformly near white with no UI. The reply reports blankness, speculates about loading and issues only WAIT; it makes no visible task-state claim.'),
    3:('no_definite_positive','The open category list actually shows Cell phones. The proposed point lies on its visible row.'),
    4:('no_definite_positive','The screenshot still shows Select a category. Saying the category seems unselected is supported; reopening is a plan.'),
    5:('no_definite_positive','The current dropdown is open and Cell phones is visible; the proposed coordinates are on its visible row.'),
    6:('no_definite_positive','The placeholder remains visible in the closed control. “Seems” about clicks is a possible cause, and the next click is a plan.'),
    7:('no_definite_positive','The open menu shows Cell phones. The normalized point is on its row; the reply does not say the choice succeeded.'),
    8:('no_definite_positive','The legal previous open frames and the current closed placeholder support that the menu closed without showing a selection.'),
    9:('no_definite_positive','The proposed normalized y=301 maps to ~217 px within the Cell phones row at the actual 720 px height. Changing x stays within the row. Cause of prior failure is tentative.'),
    10:('no_definite_positive','The current placeholder and prior open states support the reported lack of selection. Focusing then using a key is a plan.'),
    11:('definite','The list visibly shows Cell phones as the tenth named option, eleventh including the placeholder. The asserted eighth option is false, although the proposed point is on the correct row.'),
    12:('no_definite_positive','The closed menu shows its placeholder again; the alternative keyboard plan does not assert a completed selection.'),
    13:('definite','The open menu again has ten named options through Cell phones. Eighth after the placeholder is Books. The native key string is a separate action contract issue, not evidence for this semantic label.'),
}


def main():
    p=HERE/'review-packets'/PACKET; exact=HERE/'labels'/EXACT
    verify(exact)
    seal=read(p/'seal.json');source=read(p/'semantic-input.json')
    assert all(sha(p/n)==seal[n] for n in ('semantic-input.json','image-quality-input.json'))
    assert all(sha(p/n)==d for d,n in seal['original_images'].items())
    assert read(p/'image-quality-input.json')['images']==[BLANK]
    prior=read(exact/'review.json');assert sha(p/'seal.json')==prior['packet_seal_sha256']
    assert set(source['packets'])=={ALIAS}
    assert [q['decision'] for q in prior['candidate_labels'][ALIAS]]==[1]
    turns=source['packets'][ALIAS]
    assert [x['decision'] for x in turns]==list(range(1,14))
    assert turns[1]['current_image_sha256']==BLANK
    assert turns[10]['current_image_sha256']==turns[12]['current_image_sha256']==MENU
    labels=[]
    for x in turns[1:]:
        n=x['decision'];label,note=REVIEW[n]
        labels.append({'decision':n,'raw_reply_sha256':x['raw_reply_sha256'],
                       'current_image_sha256':x['current_image_sha256'],'semantic_label':label,'note':note,
                       **({'claim_type':'visible_menu_ordinal'} if label=='definite' else {})})
    dst=HERE/'labels'/str(time.time_ns());dst.mkdir(exist_ok=False)
    save(dst/'review.json',{'packet_seal_sha256':sha(p/'seal.json'),'joined_private_execution_labels':False,
        'scope_and_blinding':'Read the complete model-visible prefix and the three original images; interruption/key type was known from technical triage before semantic review. Labels are pixel-based and were sealed before joining private execution/score labels.',
        'quality_labels':{BLANK:{'label':'visually_incomplete','note':'The original frame is uniformly near white; no meaningful GUI, loading indicator, listing or result text is visible.'}},
        'candidate_labels':{ALIAS:labels}})
    save(dst/'seal.json',{'review.json':sha(dst/'review.json')})
    print(dst)


if __name__=='__main__':main()
