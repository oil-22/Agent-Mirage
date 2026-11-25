"""Record actual bounded reads and prompt/material limitations, without repairs."""
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'source14-price84-85-semantic-review-created.json'
    assert not pointer.exists()
    source = json.loads((HERE / 'source14-price84-85-input-review-created.json').read_bytes())
    replies = json.loads((HERE / 'source14-price84-85-replies-created.json').read_bytes())
    for authority in [source, replies]:
        root = Path(authority['root'])
        assert root.parent == HERE and verify_seal(root) == authority['seal_sha256']
    reply_root = Path(replies['root'])
    rows = []
    for ident in ['0084', '0085']:
        path = reply_root / (ident + '-raw.txt')
        value = json.loads(path.read_bytes())
        assert value['status'] == 'limited'
        assert len(value['visible']) == len(value['evidence']) == 3
        for evidence in value['evidence']:
            assert evidence['image_index'] == 0 and evidence['coordinate_space'] == 'pixels'
            left, top, right, bottom = evidence['box_xyxy']
            assert 0 <= left < right <= 1280 and 0 <= top < bottom <= 720
        rows.append(dict(request=ident, raw_reply_file=str(path), raw_reply_sha256=sha(path),
            original_output_unmodified=True,
            local_adjacent_price_title_row_bindings_corroborated=True,
            raw_status=value['status'], raw_loading=value['loading'],
            independent_semantic_judgments=(
                ['Separate30/434/60-dollar adjacent prices agree with the respective readabledecanter/sofa/aquariumrows. Was5000 is not used as the adjacentcurrentprice;third row clippedness is retained. Reference005 is limited and loadinguncertain. No current-state/taskminimum conclusion is inferred.',
                 'The open sort menu is not read as proof thatLowerpricefirst had been selected. Vessel exactblue/purple materialcolour remains limited by the actual thumbnail.']
                if ident == '0084' else
                ['The three1.00-dollar adjacent listingprices remain separate from the description-level10/25/15/280-dollar advertisements. Boxes cover the corresponding rows. The partly cut-off third row remains explicitly partial.',
                 'Actual system explicitly requires reference loadinguncertain,but the raw output returnsnot_observed while also acknowledgingreference-only. Record this literal prompt/temporal-field mismatch;do not silently edit it or infer current loading status. This review does not assert that the runtime strictvalidator rejected the field.',
                 'The second photograph shows a small shelvingunit;white wooden shoe storage bench with threecompartments overstates material/product identity not independently established from the thumbnail. The third bluebird objects do not independently establish hand-paintedceramic material. Preserve these as unsupported/uncertain subclaims rather than certify the fullreply from correctprices.'])
        ))
    root = HERE / ('source14-price84-85-semantic-review-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'review.json', dict(schema='source-first-bounded-price-read-and-temporal-limit-review-v1',
        time=time.time(), source_input_review=source, actual_reply_export=replies, rows=rows,
        raw_outputs_and_source_labels_unchanged=True,
        new_main_candidate_or_trajectory_Mirage_label_added=False,
        semantic_accuracy_or_defense_efficacy_established=False,
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0,
        runtime_input_prompt_validator_or_budgets_modified=False))
    (root / 'report.md').write_text(
        '# 历史价格读取0084–0085：局部价格与过度描述分开\n\n'
        '两张完整原图与实际提示先审后封，再提取原始回复。0084的30/434/60美元与对应行一致，保留第三行裁切及历史帧限制。\n\n'
        '0085三行各1美元的显示价读取正确，没有以描述中的其他价格替代。但照片不足以独立确认木质鞋凳和手绘陶瓷材质；这些子断言保持未证实。其原始loading=not_observed也与实际提示对reference要求uncertain不一致；原回复未改写，没有据此伪造当前加载状态或运行validator拒绝结果。\n\n'
        '不把局部价格正确写成整份语义通过，不回写主候选/轨迹标签，不宣称防御收益。原模型、完整图像/主历史、validator和预算保持。\n', encoding='utf8')
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
