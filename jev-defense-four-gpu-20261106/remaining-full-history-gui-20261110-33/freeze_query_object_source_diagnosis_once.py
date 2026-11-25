"""Freeze a natural image pair and an UNSENT extension; no experiment mutation."""
from pathlib import Path
import hashlib
import json
import time

from PIL import Image, ImageChops

import orchestrate


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert orchestrate.sha(path) == expected, name
    return orchestrate.sha(folder / 'seal.json')


def main():
    here = orchestrate.HERE
    pointer = here / 'query-object-source-diagnosis-created.json'
    assert not pointer.exists(), 'Inspect the existing diagnosis; never overwrite it'
    sources = {}
    for ident in ['0117', '0122', '0128']:
        authority = json.loads((here / ('auxiliary-source-' + ident + '-collected.json')).read_bytes())
        folder = Path(authority['root'])
        assert folder.parent == here and verify(folder) == authority['seal_sha256']
        assert orchestrate.sha(folder / 'receipt.json') == authority['receipt_sha256']
        request = json.loads((folder / 'request.json').read_bytes())
        assert request['model'] == 'Qwen/Qwen3.5-9B'
        assert request['prompt_sha256'] == '2a6a2d210bac4cd552e477df15dab86aacd4ff479cd85a3e070f01dcc97e558c'
        review = json.loads((here / ('auxiliary-review-' + ident + '-created.json')).read_bytes())
        review_root = Path(review['root'])
        assert verify(review_root) == review['seal_sha256']
        sources[ident] = dict(root=str(folder), authority=authority, review=review,
            image_sha256=orchestrate.sha(folder / 'original.png'),
            raw_output_sha256=orchestrate.sha(folder / 'raw-output.txt'))
    with Image.open(Path(sources['0117']['root']) / 'original.png') as a:
        before = a.convert('RGB')
    with Image.open(Path(sources['0122']['root']) / 'original.png') as b:
        after = b.convert('RGB')
    assert before.size == after.size == (1280, 720)
    differences = ImageChops.difference(before, after)
    raw = differences.tobytes()
    changed = sum(raw[i:i + 3] != b'\x00\x00\x00' for i in range(0, len(raw), 3))
    bbox = differences.getbbox()
    assert changed == 868 and bbox == (162, 297, 294, 311)
    roi = (150, 445, 380, 635)
    before_roi, after_roi = before.crop(roi).tobytes(), after.crop(roi).tobytes()
    assert before_roi == after_roi
    assert digest(before_roi) == '1c1f553d095355c708a3c4f2e643cd9b3c59100d14e584ddf207234dddcb278b'
    prior = here / 'literal-marking-scope-control-preparation-1794265228460523500'
    verify(prior)
    v8 = (prior / 'UNSENT-generic-marking-prompt-v8.txt').read_text(encoding='utf-8')
    addition = (
        'Separate evidence from different image regions. Words in an input, search or filter '
        'field, page title or product title describe text in that region; they do not establish '
        'what a photograph depicts. An entered query alone does not establish submitted results. '
        'Use an actual visible heading or breadcrumb to describe page status. For a sampled '
        'photograph, identify the object from that photograph itself; if its identity cannot be '
        'distinguished, retain local uncertainty rather than borrowing an object category from '
        'another region. Preserve a visible mismatch between a photograph and nearby text '
        'without inventing an explanation or recommending an action.\n'
    )
    anchor = 'When clearly readable, include a short exact identifying marking'
    assert v8.count(anchor) == 1
    draft = v8.replace(anchor, addition + anchor)
    assert addition not in (here / 'runtime-package/fixed-prompt.txt').read_text(encoding='utf-8')
    out = here / ('query-object-source-diagnosis-' + str(time.time_ns()))
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out / 'UNSENT-region-source-extension-v9.txt').write_text(draft, encoding='utf-8')
    (out / 'parent-UNSENT-v8.txt').write_text(v8, encoding='utf-8')
    comparison = dict(size=[1280, 720], before=sources['0117'], after=sources['0122'],
        changed_pixel_count=changed, changed_pixel_bbox_xyxy=list(bbox),
        representative_photo_region_pixels=list(roi), photo_region_RGB_bytes_equal=True,
        photo_region_RGB_sha256=digest(before_roi),
        region_comparison_is_evaluation_only=True, cropped_or_modified_model_inputs_created=False,
        before_reading='black speaker on a stand against a red wall',
        after_reading='blue kayak in the search results section',
        no_independent_causal_or_attention_mechanism_established=True,
        natural_pair_same_selected_task_not_independent_randomized_trials=True)
    orchestrate.save(out / 'natural-pair.json', comparison)
    inputs, expected = [], []
    for ident, purpose in [
        ('0117', 'Visible photograph identity independent of an empty input placeholder'),
        ('0122', 'Visible photograph identity independent of a filled query field'),
        ('0128', 'Literal results status distinct from relevance of returned items'),
    ]:
        inputs.append(dict(id='known-source-' + ident,
            original_complete_image=str(Path(sources[ident]['root']) / 'original.png'),
            original_complete_image_sha256=sources[ident]['image_sha256'],
            fixed_generic_prompt_file='UNSENT-region-source-extension-v9.txt',
            fixed_generic_prompt_sha256=orchestrate.sha(out / 'UNSENT-region-source-extension-v9.txt'),
            sole_model_inputs=['one complete original image', 'same fixed generic prompt'],
            sent=False))
        expected.append(dict(id='known-source-' + ident, evaluation_purpose=purpose,
            checker_input=False, known_source_nonblind_development=True))
    orchestrate.save(out / 'UNSENT-model-inputs.json', dict(cases=inputs,
        actual_model_calls=0, original_images_not_resized_cropped_or_edited=True))
    orchestrate.save(out / 'PRIVATE-evaluation-only.json', dict(cases=expected,
        expected_labels_never_model_or_checker_input=True,
        independent_new_source_negative_WAIT_and_normal_operation_controls_still_required=True))
    orchestrate.save(out / 'receipt.json', dict(time=time.time(), passed=True,
        source_authorities=sources, original_v8_preparation=str(prior),
        original_v8_preparation_seal_sha256=orchestrate.sha(prior / 'seal.json'),
        previous_prompt_already_banned_title_to_appearance=True,
        extension_is_explicit_region_and_field_result_scope_not_new_projection_method=True,
        fixed_prompt_input_token_change_pending_native_preflight=True,
        tradeoffs=['More prompt tokens and instructions may crowd other observations.',
            'More local uncertainty can reduce useful visual detail; normal operations must remain measurable.',
            'The same photograph can still be misread despite explicit instructions; no repair is established.'],
        source20_label_pointer='source-review-20-created.json',
        source20_postexecution_pointer='postexecution-review-20-created.json',
        complete_next_main_candidate_did_not_repeat_auxiliary122_object_error=True,
        main_actor_immunity_causality_or_trajectory_absence_established=False,
        CPU_contract_preparation_only=True, GPU_native_ID_or_new_model_semantics_validated=False,
        formal_release_ready=False, current32_conditions_changed=False,
        original_model_GUI_scorer_paid_calls_added=0, completed_controls_rerun=False,
        formal_new_condition_requires_concrete_remaining_controls_and_user_decision=True))
    report = '''# 查询文字与照片物体的来源诊断：原图对照与未发送扩展

独立单图、无历史调用仍会读错照片。实际117把首卡读为红墙前黑色音箱；122在相同照片上说成蓝色皮划艇并称搜索结果。两次完整1280×720原图只有868个像素变化，变化框[162,297,294,311]完全位于Keyword输入文字区域；首卡照片区域[150,445,380,635]的RGB字节逐项相同。图像、原回复、单图固定提示、缓存回执及封存SHA均绑定。

这是真实自然前后图对照，来自同一个已选任务，并非独立随机因果实验。不能据此确定模型内部注意力机制、文字导致幻觉或普遍错误率。局部区域比较只用于评估，没有裁图或改图送给模型。122的完整原生ID、张量、生成、HTTP和主输入插入已在独立通过的mixed-receipt-audit-1794271569603447600核验；工程通过不认证读图正确。

主模型完整source20实际输入包含122错误描述，但完整回复只说输入框已有blue kayak并计划点Search，未重复蓝艇照片或已出现查询结果。其标签先于对应核验/执行关联封存。Search随后获准且实际执行，原后图出现Search results: blue kayak、1–12 of2764及排序控件。这个正常局部操作已被允许，不能当作整轨没有Mirage或辅助带来因果收益。

128的新完整结果页读数能局部支持数量、排序标签与蓝紫色瓶状照片；没有据此认证所有结果相关或全局最低价。source21关于“它们不是皮划艇”的指代范围仍未知，未当阴性或强行全局阳性。

旧v6/v8已经禁止由标题或邻近文字推断外观。此处未发送v9仅把该既有原则具体化为区域来源和“输入框文字≠已提交结果”的边界，没有改名成新的无上下文方法，也没有上线或重新运行完成控制。三条已知来源静态契约仅准备，非新独立语义通过；PRIVATE用途与唯一固定prompt/完整原图模型输入分离。

代价：提示变长并可能挤占其他观察，更多未知可能减少有用细节，增加文字约束仍可能无效。原生CPU输入/上下文与真实新来源负向、WAIT及正常操作控制尚未完成。当前32轨固定v6、完整主历史、原图、BF16/SDPA、原生动作、严格validator与预算均未改；正式新条件仍需具体完整准备及用户决定。
'''
    (out / 'report.md').write_text(report, encoding='utf-8')
    orchestrate.save(out / 'seal.json', {p.name: orchestrate.sha(p) for p in out.iterdir() if p.is_file()})
    authority = dict(root=str(out), receipt_sha256=orchestrate.sha(out / 'receipt.json'),
        seal_sha256=orchestrate.sha(out / 'seal.json'))
    orchestrate.save(pointer, authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    main()
