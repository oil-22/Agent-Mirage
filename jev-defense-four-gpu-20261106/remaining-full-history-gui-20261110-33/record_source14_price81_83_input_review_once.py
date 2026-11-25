"""Seal source-first reviews of actual historical single-frame reads 0081-83.

Observer only. Do not read model replies or modify the running experiment.
"""
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'source14-price81-83-input-review-created.json'
    assert not pointer.exists()
    actor = json.loads((HERE / 'source-review-14-created.json').read_bytes())
    actor_root = Path(actor['review'])
    assert verify_seal(actor_root) == actor['seal_sha256']
    assert sha(actor_root / 'review.json') == actor['review_sha256']
    previous = json.loads((HERE / 'source14-price-0080-source-created.json').read_bytes())
    previous_root = Path(previous['root'])
    assert verify_seal(previous_root) == previous['seal_sha256']
    expected_system = json.loads((previous_root / 'payload.json').read_bytes())['system']
    descriptions = {
        '0081': [
            'Independently viewed the complete original homepage6f692c08 before its own reply. Keyword displays the e.g., a blue used car placeholder and a visible blue rectangular border. This border is a visible cue, not proof of operating-system focus or completed typing.',
            'Four visible LatestListings cards have adjacent150,350,1645,2200-dollar prices. The first and third titles are clipped;the bird photograph under the Canon lens title does not depict or prove a lens. Do not complete clipped text or infer prices for unseen rows.',
            'The original frame is reference002-obs002,not current task state. It does not supply a79-resultkayak query,Lowerpricefirst,boat185,an exhaustive inventory or a cheapest-blueboat conclusion. Reference loading remains uncertain.'
        ],
        '0082': [
            'Independently viewed the complete original homepage6d12ba3d before its own reply. Keyword visibly contains blue kayak and has a blue rectangular border. Category still shows Select a category;the Search button andLatestListings remain visible.',
            'The same four visible cards have150,350,1645,2200-dollar prices. Readable Keyword text is evidence of this past input field,not proof that a search had executed or that theseLatestListings are kayak results. Clipped titles and photograph/title distinctions remain.',
            'Reference003-obs003 alone does not establish a current query result,count79,price ordering,an action outcome,or a task-wide minimum. Do not inferOSfocus from the border. Reference loading remains uncertain.'
        ],
        '0083': [
            'Independently viewed the complete originalc7ff5b18 search page before its own reply. Breadcrumb and Yoursearch showbluekayak;the visible range is1-12of2764listings and sort isNewlylisted. This must remain distinct from the later79-resultkayak/lowerpricefirststate.',
            'Readable listing rows areVintageBlenkoDecanter30.00dollars,LeeIndustriesThreeCushionSofa(Was5000)434.00dollars,and a partially cut-off20gallonaquarium60.00dollars. Was5000 is title text,not the current adjacent listing price. The page bottom cuts off the third row;its unseen continuation remains unknown.',
            'The original image shows a small purple/blue glassvessel photograph,a sofa thumbnail,and an aquarium photograph;these do not supply a185-dollarbluekayak. Reference004-obs004 does not establish current browserstate,all2764results,or a task minimum. Reference loading remains uncertain.'
        ]
    }
    rows = []
    for ident, notes in descriptions.items():
        entry = json.loads((HERE / ('source14-price-' + ident + '-source-created.json')).read_bytes())
        source = Path(entry['root'])
        assert source.parent == HERE
        assert verify_seal(source) == entry['seal_sha256']
        payload = json.loads((source / 'payload.json').read_bytes())
        receipt = json.loads((source / 'receipt.json').read_bytes())
        assert payload['system'] == expected_system
        assert payload['candidate'] is None and payload['operation'] == 'judge'
        assert len(payload['view']['messages']) == len(payload['view']['images']) == 1
        assert payload['view']['images'][0]['role'] == 'reference'
        assert payload['view']['messages'][0]['role'] == 'user'
        rows.append(dict(request=ident, source_input=str(source),
            source_input_seal_sha256=entry['seal_sha256'], actual_images=receipt['images'],
            all_actual_system_and_messages_read=True,
            same_single_frame_system_as_reviewed_0080=True,
            full_original_image_independently_viewed=True,
            raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=notes))
    target = HERE / ('source14-price81-83-input-review-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(target / 'review.json', dict(
        schema='source-first-historical-price-reader-input-review-v1', time=time.time(),
        rows=rows, actor_source_label_authority=actor,
        raw_own_replies_not_read_before_this_seal=True,
        one_reviewer_not_fully_blind_or_human_gold=True,
        prior_source14_and_earlier_reader_diagnoses_known=True,
        no_new_actor_labels_or_trajectory_negatives_inferred=True,
        original_scope32_and_original_budgets_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0,
        runtime_model_prompt_input_validator_or_budgets_modified=False))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=sha(target / 'review.json'),
                  seal_sha256=sha(target / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
