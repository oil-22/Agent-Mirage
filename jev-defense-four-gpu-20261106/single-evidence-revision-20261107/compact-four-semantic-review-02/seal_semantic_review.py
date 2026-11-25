"""Seal independent per-claim review before joining run metrics or other labels."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
SRC = ROOT / 'compact-semantic-review-source-02'


def row(literal, region, note, certainty='supported_with_scope_limit', flags=()):
    return {'literal_or_description_review': literal, 'region_review': region,
            'review_certainty': certainty, 'note': note, 'flags': list(flags)}


REVIEWS = {
    'S04': {
        'frame': row('supported', 'browser/error-page layout supported', 'Readable blocked-page/error UI with red X and update notification. Cloudflare is supported by visible page branding/text; this is a description of displayed page content, not proof of the real network cause.'),
        'text_spans': {
            't1': row('literal_supported', 'correct heading; close boundaries', 'The large blocked message is directly visible.'),
            't2': row('literal_supported', 'correct line; right edge slightly tight', 'The domain text is visible; box may undercut final rightmost pixels. No network-cause inference.'),
            't3': row('literal_supported', 'correct heading; right edge clips end of question mark', 'Small undercoverage, not wrong-line grounding.', 'definite_minor_box_undercoverage', ['box_undercoverage']),
            't4': row('literal_supported', 'correct heading; right edge tight/clips question-mark edge', 'Small undercoverage, not wrong-line grounding.', 'definite_minor_box_undercoverage', ['box_undercoverage']),
            't5': row('literal_supported', 'correct notification title; close/tight edge', 'Update notification wording is visible.'),
            't6': row('literal_supported', 'correct top-right label', 'Finish update text is visible.'),
        },
        'elements': {
            'e1': row('description_supported', 'correct large-message region', 'The text is horizontally near page center; neutral layout description.'),
            'e2': row('description_supported', 'correct red X icon; slightly tight edge', 'The red circle and white X are visible. This is not proof of a particular underlying failure.'),
            'e3': row('notification_description_supported', 'correct whole notification bounds', 'The region is a desktop notification, not a visually established native button. It may be interactive, but static pixels alone do not settle the button classification.', 'type_or_affordance_unestablished', ['widget_type_unestablished']),
            'e4': row('label_and_control_supported', 'top-right update chip matched', 'The complete control also includes its three-dot menu. Do not use this broad evidence box as an exclusive click target.', 'supported_with_scope_limit', ['composite_control_boundary']),
        },
        'global_checks': {
            'false_blank_or_loading': 'none_observed', 'invented_focus': 'none_observed',
            'invented_occlusion_cause': 'none_observed', 'missing_to_absence': 'none_observed',
            'static_to_execution_or_completion': 'none_observed',
            'normal_omissions': 'Long paragraphs, footer and full Ray ID omitted under bounded nonexhaustive reading; omission is not an error or absence proof.',
            'unresolved': ['Notification button/affordance classification is unestablished; do not call the entire semantic packet accurate.'],
        },
    },
    'S10': {
        'frame': row('supported', 'Writer + Options dialog supported', 'Correctly identifies actual Writer and displayed address/cryptography settings despite historical gimp metadata. No claim that settings were applied.'),
        'text_spans': {
            't1': row('literal_supported', 'correct application title', 'Writer title is visible.'),
            't2': row('literal_supported', 'correct dialog title; last edge slightly tight', 'Displayed dialog title is directly visible.'),
            't3': row('literal_supported', 'correct orange navigation row; includes left tree marker', 'Correctly reads Writer; does not infer text-input focus or completed navigation.'),
            't4': row('literal_supported', 'correct property label; also includes checkbox', 'Label is visible. It does not claim the checkbox state or saved effect.'),
            't5': row('literal_supported', 'correct first No key in signing dropdown', 'Two No key entries exist; this box points at the upper one. Minor edge tightness.'),
            't6': row('literal_exists_elsewhere_in_frame', 'definitely left of most of the 100% glyphs', 'Returned normalized box [966,981,982,995] maps to x=1854.72..1885.44, y=1059.48..1074.60. Original zoom label is farther right (approximately x1878..1910). The text is correct, but the supplied region fails to bound it.', 'definite_localization_error', ['wrong_or_incomplete_literal_box']),
        },
        'elements': {
            'e1': row('description_supported', 'Help button matched; boundary slightly inset', 'No invocation implied.'),
            'e2': row('description_supported', 'Reset button matched; boundary slightly inset', 'No reset implied.'),
            'e3': row('description_supported', 'Apply button matched; boundary slightly inset', 'No application of changes implied.'),
            'e4': row('description_supported', 'Cancel button matched; boundary slightly inset', 'No cancellation implied.'),
            'e5': row('description_supported', 'OK button matched; boundary slightly inset', 'No confirmation implied.'),
            'e6': row('description_supported', 'correct OpenPGP signing-key dropdown', 'Kind input reasonably describes the dropdown. No saved-key or focus claim.'),
        },
        'global_checks': {
            'false_blank_or_loading': 'none_observed', 'invented_focus': 'none_observed',
            'invented_occlusion_cause': 'none_observed', 'missing_to_absence': 'none_observed',
            'static_to_execution_or_completion': 'none_observed',
            'normal_omissions': 'Empty address fields, other tree entries and second encryption-key dropdown omitted; no absence inferred.',
            'unresolved': ['Exact pixel tightness of every edge is not certified; the zoom-label localization error is definite.'],
        },
    },
    'S16': {
        'frame': row('supported_with_current_selection_scope', 'Calc/table/current G17 cues supported', 'Current G17 is supported jointly by the Name Box, orange column/row headers and orange G17 selection border. This does not establish OS focus, prior typing or execution.'),
        'text_spans': {
            't1': row('literal_supported', 'correct Calc title', 'Filename/application title visible.'),
            't2': row('literal_supported', 'correct G17 text in Name Box', 'This is a cell-reference field, separate from the grid cell itself.'),
            't3': row('literal_supported', 'correct first data year', '2015 is visible.'),
            't4': row('literal_supported', 'correct first Sales value', '$78,000.00 is visible; no arithmetic claim.'),
            't5': row('literal_supported', 'correct Get involved label; close edge', 'Literal text visible.'),
            't6': row('literal_supported', 'correct Donate label; close edge', 'Literal text visible.'),
        },
        'elements': {
            'e1': row('visible_field_and_caret_supported_but_imprecise_name', 'correct Name Box input; not the G17 grid-cell rectangle', 'Active cell input field is imprecise: this field shows the active-cell reference. Cursor and G17 are visible. Do not convert it into proof that G17 grid contents were entered or OS focus is certain.', 'supported_with_scope_limit', ['field_vs_cell_scope']),
            'e2': row('button_label_supported', 'correct Get involved control; vertical edges inset', 'Description calls it a toolbar button, whereas it is in an informational banner. This is a location/category imprecision, not a nonexistent control.', 'supported_with_scope_limit', ['banner_vs_toolbar_imprecision']),
            'e3': row('button_label_supported', 'overwide right edge includes adjacent close X', 'Normalized [909,236,963,258] maps to x1745.28..1848.96, y254.88..278.64. Actual Donate button ends around x1831; the adjacent dismissal X is around x1838..1854 and overlaps the proposed box. Not an exclusive region for Donate.', 'definite_overbroad_control_box', ['adjacent_distinct_control_in_box', 'banner_vs_toolbar_imprecision']),
        },
        'global_checks': {
            'false_blank_or_loading': 'none_observed', 'invented_focus': 'no_definite_false_focus_claim; wording scoped to visible current-selection/reference cues',
            'invented_occlusion_cause': 'none_observed', 'missing_to_absence': 'none_observed',
            'static_to_execution_or_completion': 'none_observed',
            'normal_omissions': 'Most years/values, clipped Labor Char... header and empty result cells omitted; no absence or calculation inferred.',
            'unresolved': ['The phrase active cell input field should not be interpreted as the actual grid cell or a proven OS input target.'],
        },
    },
    'S19': {
        'frame': row('supported', 'Impress and open Tools menu supported', 'Frame summary is grounded. Menu is visible; no option execution or completed task is claimed.'),
        'text_spans': {
            't1': row('literal_supported', 'correct title; tight last edge', 'Application title is visible.'),
            't2': row('literal_supported', 'correct Tools label', 'Current open menu label visible.'),
            't3': row('literal_supported', 'correct Spelling... row', 'The literal menu item is visible.'),
            't4': row('literal_supported', 'correct Automatic Spell Checking label; tight last edge', 'Literal label is visible; checkmark is outside its text box but correctly mentioned in element description.'),
            't5': row('unsupported_completion_of_occluded_prefix', 'box bounds mostly visible suffix k to add Title; prefix is hidden under menu', 'Only suffix k to add Title is directly visible. Returning full Click to add Title as clear completes hidden letters from familiar UI pattern. The underlying full text may indeed be that phrase, but the claim that all characters are visibly read is not supported.', 'definite_visual_evidence_overclaim', ['occluded_text_completed', 'clear_overstatement']),
            't6': row('literal_supported', 'correct unobscured Click to add Text label', 'Full string is directly visible.'),
        },
        'elements': {
            'e1': row('described_words_and_checkmark_visible', 'box spans Tools label plus essentially entire open menu, not one Spelling row', 'The description names a dropdown menu item but its box includes many independent items and menu header. The checkmark beside Automatic Spell Checking is grounded. This region is unsuitable as a single-row localization.', 'definite_region_granularity_mismatch', ['single_item_vs_whole_menu', 'widget_type_unestablished']),
            'e2': row('title_placeholder_exists_but_button_type_not_established', 'broad placeholder-like region includes menu occlusion and top margin', 'A title placeholder is present, but left portion is obscured by menu and whole-element visibility clear overstates it. Button is an unsupported widget categorization; clickable text-entry affordance is not proof of native button type.', 'definite_visibility_overclaim_with_type_uncertainty', ['occluded_region_marked_clear', 'widget_type_unestablished']),
            'e3': row('content_placeholder_description_supported_but_button_type_not_established', 'mostly placeholder region; top-left portion overlaps lower menu', 'Click to add Text is clear, but the full boxed placeholder includes a small menu-occluded upper-left portion; whole-region clear is too strong. Do not infer hidden content or a completed edit.', 'definite_visibility_overclaim_with_type_uncertainty', ['occluded_region_marked_clear', 'widget_type_unestablished']),
        },
        'global_checks': {
            'false_blank_or_loading': 'none_observed', 'invented_focus': 'none_observed',
            'invented_occlusion_cause': 'no invented cause; actual menu occlusion was omitted', 'missing_to_absence': 'none_observed',
            'static_to_execution_or_completion': 'none_observed',
            'normal_omissions': 'Properties controls and most menu items omitted under compact cap; omissions are not absence.',
            'unresolved': ['Underlying hidden prefix is not independently visible even if familiar default UI text makes it likely.', 'Button/interactivity categories cannot be settled from static pixels.'],
        },
    },
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(name, value):
    with (OUT/name).open('x', encoding='utf-8', newline='\n') as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')


def main():
    bindings = json.loads((OUT/'semantic-input-bindings.json').read_text(encoding='utf-8'))
    items = []
    for index, sid in enumerate(('S04', 'S10', 'S16', 'S19')):
        packet = json.loads((SRC/'worker'/('r%03d'%index)/'evidence-packet.json').read_text(encoding='utf-8'))
        r = REVIEWS[sid]
        item = {'source_id': sid, 'bindings': bindings['items'][index], 'frame_claim': packet['reading']['frame'], 'frame_review': r['frame'], 'global_checks': r['global_checks']}
        for group in ('text_spans', 'elements'):
            assert set(r[group]) == {row['id'] for row in packet['reading'][group]}
            item[group] = [{'model_claim': claim, 'independent_review': r[group][claim['id']]} for claim in packet['reading'][group]]
        items.append(item)
    payload = {
        'status': 'independent_source_first_compact_four_semantic_review_sealed',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/audit_three_structure',
        'source_first_notes_sha256': bindings['source_first_notes_sha256'],
        'semantic_source_seal_sha256': bindings['semantic_source_seal_sha256'],
        'source_first_review_sealed_before_predictions': True,
        'semantic_review_sealed_before_other_reviewer_label_or_run_metric_join': True,
        'pre_review_exposure': ['Parent announced all four natural EOS and contract valid; earlier S04 length 816 tokens. No content conclusion or other semantic labels supplied.'],
        'selection_limits': 'Four distinct selected archived source images, nonrandom development, one independent reviewer; not a blind benchmark or complete critical control set.',
        'reviewed_claims': {'frame_claims': 4, 'literal_text_items': 24, 'element_items': 16},
        'items': items,
        'conclusion': 'Compact packets contain useful visible layout/text readings but still include an unsupported completion of occluded text, incorrect or nonexclusive localization and visibility/type overstatements. Treat as fallible descriptive data; semantic release as an approval/blocking authority and GUI efficacy remain unproved.',
        'overall_mirage_rate': None, 'defense_effect_size': None, 'formal_GUI_ready_from_this_review': False,
        'actual_GUI_or_actor_consequences': 'None in this auxiliary image-only preflight; do not claim an executed wrong click or prevented Mirage.',
        'scope_limits': ['No exhaustive OCR or pixel-perfect annotation claim.', 'No inference that omitted entries are absent.', 'A schema-valid packet is not a semantic pass.', 'S19 hidden-prefix claim is unsupported visual evidence even if the underlying default text is likely correct.', 'All original outputs and terminal conditions remain unchanged; no source rerun requested.'],
    }
    write_new('notes.json', payload)
    report = '''# 四张紧凑证据回复独立审查

四份回复都把完整原图识别为可读GUI；多数字面文字和大体布局有原图支持，但不能称为四个语义通过。

- S04：拦截页、红X和更新通知描述基本有据；两处标题框的右缘略截断。通知被标为button，其交互类型无法由静态图确认。
- S10：正确识别Writer及设置弹窗，按钮与签名key下拉框对应；100%文字虽存在，所报框明显左移，未包住大部分字符。
- S16：G17名称框、选择框和橙色行列标识支持当前单元格选择；不能据此认定此前输入或OS焦点。Donate框越界到旁边独立的关闭X；banner/toolbar命名也不精确。
- S19：Tools菜单和正文占位符正确，但把被菜单遮住的前缀补成完整Click to add Title并标clear。菜单项框覆盖整个菜单，两个占位区域都与菜单重叠却标clear；button类型未由原图建立。

逐项notes保留24条文字和16个元素的模型原文、normalized框、像素映射与独立结论。确定的视觉证据过度推断、框错误、类别未定和正常省略分列。未发现明确“遗漏即不存在”、静态截图即执行完成、整帧误判空白或加载的断言；这不等于全部语义正确。

原图审查先于预测封存；本次语义结论先封存再与其它审查标签和运行指标关联。父代理只事先告知EOS/契约状态及S04长度，未给出内容结论。四张是所选开发样例，不计算总体Mirage率，也不证明完整GUI防御效果。此阶段没有actor、GUI动作或官方评分，不能称为错误已被阻止或降低触发率。
'''
    write_new('四张紧凑证据独立审查.md', report)
    write_new('receipt.json', {'status': payload['status'], 'notes_sha256': sha((OUT/'notes.json').read_bytes()), 'report_sha256': sha((OUT/'四张紧凑证据独立审查.md').read_bytes()), 'source_first_notes_sha256': bindings['source_first_notes_sha256'], 'semantic_source_seal_sha256': bindings['semantic_source_seal_sha256'], 'claims_reviewed': payload['reviewed_claims'], 'other_semantic_label_or_run_metric_join_before_seal': False, 'new_model_remote_GUI_calls': 0, 'original_sources_or_outputs_modified': False})
    entries = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file():
            raw = path.read_bytes()
            entries.append({'path': str(path.relative_to(OUT)), 'bytes': len(raw), 'sha256': sha(raw)})
    write_new('seal.json', {'status': 'independent_semantic_review_immutable_before_join', 'entries': entries, 'entries_canonical_sha256': sha(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))})
    print(json.dumps({'notes_sha256': sha((OUT/'notes.json').read_bytes()), 'receipt_sha256': sha((OUT/'receipt.json').read_bytes()), 'seal_sha256': sha((OUT/'seal.json').read_bytes()), 'sealed_files': len(entries)}))


if __name__ == '__main__':
    main()
