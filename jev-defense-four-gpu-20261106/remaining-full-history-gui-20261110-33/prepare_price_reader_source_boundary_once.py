"""Freeze an UNSENT generic primary-reader prompt change for actual source errors."""
import difflib
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'price-reader-source-boundary-preparation-created.json'
    assert not pointer.exists()
    authorities = []
    for name in ['source14-price84-85-semantic-review-created.json',
                 'source14-price86-87-semantic-review-created.json',
                 'source14-price88-semantic-review-created.json']:
        authority = json.loads((HERE / name).read_bytes())
        source = Path(authority['root'])
        assert source.parent == HERE and verify_seal(source) == authority['seal_sha256']
        assert sha(source / 'review.json') == authority['review_sha256']
        authorities.append(authority)
    input_authority = json.loads((HERE / 'source14-price-0088-source-created.json').read_bytes())
    source = Path(input_authority['root'])
    assert verify_seal(source) == input_authority['seal_sha256']
    original = json.loads((source / 'payload.json').read_bytes())['system']
    addition = '''
Keep image content separate from adjacent advertising text. Describe a small photo's
visible shape and colour; material, manufacturing method and exact product identity
remain unknown unless independently legible or visually established in this image.
Literal query-field text is not proof the displayed results have refreshed. When
referring to a query, distinguish the visible result heading/breadcrumb from the
input field; if they differ, retain both literal observations and execution uncertainty.
A visible sort-menu option is not evidence that option is selected or was executed.
For this reference-only reading, loading must remain uncertain; never infer current
loading, completed typing, focus, search execution or result freshness from these pixels.
'''
    expected = 'Do not give advice or actions. Include all required fields and end the JSON once.\n'
    assert original.count(expected) == 1
    proposed = original.replace(expected, addition + expected)
    for token in ['aruba', 'Grizzly', 'Akron', 'kayak', 'ceramic', '185', '2764', '79']:
        assert token.casefold() not in proposed.casefold()
    root = HERE / ('price-reader-source-boundary-preparation-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'original-running-primary-single-frame-prompt.txt').write_bytes(original.encode('utf8'))
    (root / 'UNSENT-primary-source-boundary-prompt.txt').write_bytes(proposed.encode('utf8'))
    (root / 'proposed.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), proposed.splitlines(True),
        fromfile='running-primary-price-reader', tofile='UNSENT-source-boundary-reader')), encoding='utf8')
    controls = [
        dict(source='source14-price-0082-source-created.json',
             boundary='A filled query field on a homepage is not a completed search;latest cards remain their actual source.'),
        dict(source='source14-price-0084-source-created.json',
             boundary='The sort menu is open,but the selected sort is distinct from the unselected option text.'),
        dict(source='source14-price-0085-source-created.json',
             boundary='Correct adjacent listingprices stay readable even when tiny material/product identity is unknown.'),
        dict(source='source14-price-0088-source-created.json',
             boundary='Edited input and old resultbreadcrumb differ;retain execution uncertainty and original resultcount.'),
        dict(source='source14-price-0081-source-created.json',
             boundary='Keep photograph content separate from a title advertising a different object.'),
        dict(source='auxiliary-source-0066-1794261362949992500',
             boundary='Read local title/price and visible photograph independently;do not infer minimum or material certainty.')
    ]
    save(root / 'PRIVATE-known-source-controls.json', dict(
        evaluation_only_never_model_input=True, source_selected_nonblind=True,
        synthetic_cases_not_new_model_replies=True, controls=controls,
        no_control_or_terminal_reexecuted=True))
    save(root / 'receipt.json', dict(schema='UNSENT-primary-source-boundary-prompt-v1',
        time=time.time(), actual_source_input=input_authority, preceding_semantic_diagnoses=authorities,
        original_prompt_sha256=sha(root / 'original-running-primary-single-frame-prompt.txt'),
        proposed_prompt_sha256=sha(root / 'UNSENT-primary-source-boundary-prompt.txt'),
        unchanged_required_response_fields=['status','visible','limitations','loading','evidence','reason'],
        no_task_candidate_history_expected_answer_or_prior_reply_added=True,
        exact_tradeoff='More boundary instructions may consume attention/outputbudget or reduce identity detail;this does not establish literalreading accuracy. A conservative unknown material must not suppress separately readable title/adjacentprice facts.',
        all_original_readable_row_requirements_and_strict_validator_retained=True,
        historical_price_dispatch_and_full_actor_history_unchanged=True,
        actual_budget_savings_or_false_block_reduction_unproven=True,
        current32_not_modified=True, proposed_prompt_unsent=True,
        native_forward_Generation_and_new_source_negative_WAIT_preflights_not_completed=True,
        future_condition_not_authorized_or_launched_by_this_receipt=True,
        no_model_GUI_scorer_paid_calls=0, efficacy_established=False, goal='active'))
    (root / 'report.md').write_text(
        '# 主核验逐图读取：来源边界提示草案（未发送）\n\n'
        '来源为已经先审封存的0085–0088实际问题：材料/商品身份超读、reference加载字段不一致、把输入框新文本当成已刷新结果。\n\n'
        '草案只加入通用边界：照片内容与广告标题分开；输入框与结果面包屑分开；菜单选项与已选排序分开；历史帧不证明当前执行/加载。保留原六字段、逐行标题与显示价要求、完整原图及strict validator。没有任务、具体商品、数字答案或私人标签进入提示。\n\n'
        '代价是更长指令可能挤占预算/注意力并减少身份细节；未知材质不能挡住可读标题和价格。静态准备不证明语义修复或节省调用，尚需新来源负向/WAIT/正常操作控制与原生预检。当前32轨、路由和全部预算不变，0新推理/GUI/scorer，无旧终局重跑。\n', encoding='utf8')
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
