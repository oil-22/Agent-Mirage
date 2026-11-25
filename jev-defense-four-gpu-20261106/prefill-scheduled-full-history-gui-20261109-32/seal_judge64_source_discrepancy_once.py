"""Preserve an evaluation-only source discrepancy without changing runtime."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'judge64-source-discrepancy-created.json').exists()
    follow = read(HERE / 'candidate22-followup-created.json')
    root = Path(follow['root'])
    assert sha(root / 'seal.json') == follow['seal_sha256']
    for name, expected in read(root / 'seal.json').items():
        assert sha(root / name) == expected, name
    bound = read(root / 'judge64-source-binding.json')
    reply = json.loads(bound['native_response_text'])
    evidence = reply['action']['evidence'][0]
    quote = "Current screenshot showing search results for 'blue kayak' with a list of items and pagination controls at the bottom."
    assert evidence['description'] == quote
    assert evidence['observation_id'] == '022-obs022' and evidence['image_index'] == 0
    current = HERE / 'source-first-packets/1794233180627760800/9da9deeee4f6ef35f3a9/image-21.png'
    assert sha(current) == bound['actual_public_image_inventory'][0]['sha256'] == '019f34bbae1b72b0b6426ae074a68bd225ae956646151c7c635ad832e8f530d8'
    review = read(HERE / 'source-review-05-created.json')
    reviewpath = Path(review['review']) / 'review.json'
    assert sha(reviewpath) == review['review_sha256']
    joined = HERE / 'post-review-join-1794233314583525500/join.json'
    assert sha(joined) == read(joined.parent / 'seal.json')['join.json']
    join = read(joined)['rows'][0]
    assert join['accepted'] and join['executed']
    post = root / '023-originally-captured.png'
    frame = read(root / 'frame-receipt.json')
    assert sha(post) == frame['next_observation_current_image']['sha256']
    out = HERE / ('judge64-source-discrepancy-' + str(time.time_ns()))
    out.mkdir()
    (out / 'current-original.png').write_bytes(current.read_bytes())
    (out / 'postexecution-original.png').write_bytes(post.read_bytes())
    row = {
        'schema': 'evaluation-only-current-frame-evidence-description-discrepancy-v1',
        'time': time.time(), 'evaluation_only_never_checker_input': True,
        'candidate': '<action>{"type":"scroll","direction":"down"}</action>',
        'candidate_source_review': str(reviewpath), 'candidate_source_review_sha256': sha(reviewpath),
        'candidate_label_unchanged': True, 'candidate_definite_semantic_Mirage': False,
        'native_action_target_or_direction_error': False,
        'current_image_source_SHA': sha(current), 'current_image_independently_viewed_by_root': True,
        'actual_judge_binding': str(root / 'judge64-source-binding.json'),
        'actual_judge_binding_sha256': sha(root / 'judge64-source-binding.json'),
        'actual_judge64_natural_EOS': bound['natural_EOS'],
        'unsupported_current_frame_quote': quote,
        'source_discrepancy': 'The cited current image0is the top of the results with literal49-60of2764, '
                              'blue kayak search and Lower price first sort. The visible lower edge cuts '
                              'through the doll listing; no pagination control is visible in this frame. '
                              'Older history includes pagination, but cannot make a current-image0 '
                              'description true. The exact cause of this misdescription is not established.',
        'separate_action_assessment': 'Scroll down is a reasonable exploratory action, accepted and '
                                      'executed with0recaptures/0regenerations in this decision. '
                                      'This record does not relabel the action as a Mirage or a wrong action.',
        'postexecution_frame': str(post), 'postexecution_frame_sha256': sha(post),
        'postexecution_frame_viewed': 'Coherent mid-listings after scrolling, including vases, Samsung '
                                     'Galaxy S7Edge phone cases, a flying-saucer pet toy and blue drinking '
                                     'glasses. This is local normal movement, not task success.',
        'execution_join': str(joined), 'execution_join_sha256': sha(joined),
        'reviewer': 'Root source author, single reviewer; not fully blind or independent human gold',
        'new_model_GUI_capture_agent_action_scorer_paid_calls': 0,
        'runtime_condition_validator_action_budget_or_prompt_changed': False,
        'repair_not_integrated_or_semantically_validated': True,
        'trajectory_Mirage': None, 'efficacy_established': False,
    }
    save(out / 'review.json', row)
    text = ('# 核验器当前图来源误描述：候选22\n\n'
            '原生候选仅向下滚动，无事实、历史或完成断言。先审原图/合法历史封存后，'
            '关联到原Controller接受并执行，0重截图、0再生成；动作本身正常。\n\n'
            '实际judge64自然EOS回复把image0描述成含有“pagination controls at the bottom”。'
            '该当前图为49–60/2764列表顶部，底边截在玩偶商品，未显示分页控件。'
            '历史中的分页图不能支持这个当前图描述；具体误读原因未证明。'
            '这是核验器的来源描述错误，候选本身的语义标签保持不变。\n\n'
            '实际后图已查看：花瓶、手机壳、宠物玩具与蓝玻璃杯，页面正常向下展开。'
            '这不构成任务完成、整轨0Mirage或辅助收益证据。单一来源作者审查，非完全盲人工gold。\n\n'
            '报告和两张原图仅供评估，不进入checker。0新增模型/GUI/评分；未热改当前条件。'
            '取证导出器的元数据结构错误已原件封存，仅linked修复读取原始图片字节，'
            '复用已导出的后图，没有重跑完成推理。目标ACTIVE。\n')
    (out / '核验器当前图来源误描述-候选22.md').write_text(text, encoding='utf8')
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = {'root': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'judge64-source-discrepancy-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
