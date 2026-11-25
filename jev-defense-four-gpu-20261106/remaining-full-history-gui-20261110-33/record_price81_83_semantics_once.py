"""Record independent bounded semantics after the source-first 0081-83 seal."""
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'source14-price81-83-semantic-review-created.json'
    assert not pointer.exists()
    source = json.loads((HERE / 'source14-price81-83-input-review-created.json').read_bytes())
    replies = json.loads((HERE / 'source14-price81-83-replies-created.json').read_bytes())
    source_root, reply_root = Path(source['root']), Path(replies['root'])
    for authority, root in [(source, source_root), (replies, reply_root)]:
        assert root.parent == HERE
        assert verify_seal(root) == authority['seal_sha256']
    assert sha(source_root / 'review.json') == source['review_sha256']
    notes = {
        '0081': [
            'Four adjacent listing prices150,350,1645,2200dollars and their respective cards have visible support. Clipped speaker/lens titles are retained as clipped. The birdphoto is kept distinct from the Canon lens title. The console support surface does not establish a particular separate stand construction.',
            'All four citation boxes cover the corresponding visible photograph,title andprice areas. Reference002 facts are reported aslimited/past;loadinguncertain and no cheapest-blueboat/current-state claim is made.'
        ],
        '0082': [
            'Four local cardprice bindings agree with the original frame;birdphoto is again distinct from its lens title. The reason correctly reports the visiblebluekayak Keyword but uses genericsearchpage wording;it does not assert a completed search or that theseLatestListings are query results.',
            'All four citation boxes cover the respective visible cardcontent. Reference003 islimited/past/loadinguncertain. There is no79-resultclaim,orderingclaim,boat185claim or taskminimum conclusion.'
        ],
        '0083': [
            'The actual three readable identities and adjacent30,434,60-dollar listing prices are separately bound to their corresponding rows. TheWas5000 title qualifier is not substituted for the434-dollar adjacentlistingprice. The partly cut-off aquarium row remains explicitly partial.',
            'Each citation covers the corresponding readable row within1280x720bounds,including the third frame-edgebox endingy720. The small vessel photograph has blue/purple tones;its exact productcolour is not established as a qualifyingboatcolour. Reference004 islimited/past/loadinguncertain with no globalminimum or completed-action claim.'
        ]
    }
    rows = []
    for ident, count in [('0081', 4), ('0082', 4), ('0083', 3)]:
        raw = (reply_root / (ident + '-raw.txt')).read_text(encoding='utf8')
        decoded = json.loads(raw)
        assert decoded['status'] == 'limited' and decoded['loading'] == 'uncertain'
        assert len(decoded['visible']) == len(decoded['evidence']) == count
        for citation in decoded['evidence']:
            assert citation['image_index'] == 0 and citation['coordinate_space'] == 'pixels'
            left, top, right, bottom = citation['box_xyxy']
            assert 0 <= left < right <= 1280 and 0 <= top < bottom <= 720
        rows.append(dict(request=ident, raw_reply_file=str(reply_root / (ident + '-raw.txt')),
            raw_reply_file_sha256=sha(reply_root / (ident + '-raw.txt')),
            original_reply_unchanged=True, source_first_input_authority=source,
            local_price_title_row_bindings_corroborated=True,
            independent_semantic_judgments=notes[ident],
            full_reply_semantic_accuracy_label=None,
            new_main_candidate_or_trajectory_label_added=False))
    target = HERE / ('source14-price81-83-semantic-review-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    review = dict(schema='source-first-historical-reader-semantic-review-v1', time=time.time(),
        source_input_review=source, actual_reply_export=replies, rows=rows,
        source_labels_and_original_outcomes_unchanged=True,
        readings_not_reinterpreted_as_current_image_or_task_minimum=True,
        all_history_scan_scope_diagnosis_preserved=True,
        no_claim_of_auxiliary_causal_benefit_or_defense_efficacy=True,
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0,
        runtime_input_prompt_validator_or_budget_modified=False)
    save(target / 'review.json', review)
    (target / 'report.md').write_text(
        '# 历史逐图价格读取0081–0083独立审查\n\n'
        '三份完整原图和实际原生提示先读后封，随后提取对应原始回复；请求/回复/输入ID与跨机来源已按原回执审计。\n\n'
        '0081、0082分别是空关键词和已输入blue kayak的历史首页。四张卡片的150/350/1645/2200美元局部归属有原图支持，鸟照片未被镜头标题替代；输入文字不证明搜索已经完成。\n\n'
        '0083是早期blue kayak搜索，原图是1–12/2764、Newly listed。三行30/434/60美元分别对应醒酒器、沙发、鱼缸，Was5000未代替当前434美元；第三行截断保留。小器皿的蓝紫色不构成蓝艇颜色证据。\n\n'
        '三次均保留reference/past、limited和loading uncertain，没有推出当前状态、79条查询或最便宜蓝艇。局部价格读取正确不认证整个主候选；型号错误与最低价范围未知分别保留，不新增整轨阴性或防御收益。原运行v6、主完整历史/原图、strict validator和全部原预算均未改。\n',
        encoding='utf8')
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=sha(target / 'review.json'),
                  seal_sha256=sha(target / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
