"""Bind the sealed new source review to reused old replies and publish results."""
import ast
import base64
import hashlib
import json
import re
import time
from pathlib import Path
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON


REVIEW = HERE / 'offline10-new-source-review-1794683247839693800'
PACKETS = HERE / 'offline10-receipt-repair-semantic-packets-1794683024185861700'
AUDIT = HERE / 'offline10-receipt-repair-postexit-audit-1794682964578820400'
PARENT_RAW = HERE / 'fresh-exited-parent-raw-1794674765901374600'
REGISTRY = HERE / 'semantic-coverage-registry-1794681968796492900'
PREP = HERE / 'approved-offline-receipt-repair-01'


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    seal = load(root / 'seal.json')
    assert all(sha(root / n) == h for n, h in seal.items())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


BRIDGE = r'''
rows=[]
for expected in EXPECTED:
 d=Path(expected['folder'])
 assert str(d).startswith('/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked11/primary/requests/')
 assert sha(d/'seal.json')==expected['seal_sha256']
 seal=json.loads((d/'seal.json').read_bytes())
 assert sha(d/'body.json')==seal['body.json']==expected['original_body_file_sha256']
 body=json.loads((d/'body.json').read_bytes())
 canonical_sha=hashlib.sha256(canonical(body)).hexdigest()
 assert canonical_sha==expected['canonical_body_sha256']
 assert sha(d/'wire-request.bin')==seal['wire-request.bin']==expected['wire_sha256']
 wire=json.loads((d/'wire-request.bin').read_bytes())
 assert wire['request_id']==expected['request_id']and wire['body']==body
 assert sha(d/'response.json')==seal['response.json']
 response=json.loads((d/'response.json').read_bytes())
 assert response['request_id']==expected['request_id']and response['text']==expected['native_text']
 rows.append({'case':expected['case'],'request_id':expected['request_id'],
  'original_body_file_sha256':sha(d/'body.json'),'canonical_body_sha256':canonical_sha,
  'wire_sha256':sha(d/'wire-request.bin'),'source_request_seal_sha256':sha(d/'seal.json'),
  'response_sha256':sha(d/'response.json'),'exact_file_object_wire_reply_bridge_verified':True})
print(json.dumps({'rows':rows,'new_model_GUI_calls':0,'only_ten_source_metadata_bridges_not_a_repeated_full_audit':True}))
'''


def main():
    pointer = HERE / 'offline10-comparison-current.json'
    assert not pointer.exists(), 'Read the existing immutable comparison'
    for root in [REVIEW, AUDIT, PARENT_RAW, REGISTRY]:
        verify(root)
    # New judgments are already sealed before the explicit baseline-label join.
    new = load(REVIEW / 'review.json')
    assert new['new_candidates_reviewed_before_explicit_old_label_join']
    sources = load(PACKETS / 'PRIVATE-source-index.json')
    old = {v['folder']: v for v in load(PARENT_RAW / '3090.json')['sealed_main_requests']}
    labels = {v['request_id']: v for v in load(REGISTRY / 'registry.json')['rows']}
    plan = {v['case']: v for v in load(PREP / 'package/development-plan.json')['inputs']}
    expected, selected = [], {}
    for source in sources:
        n = source['case']
        actual = old[source['original_request']]
        label = labels[actual['request_id']]
        assert label['candidate'] == n and label['request_seal_sha256'] == actual['seal_sha256']
        assert actual['natural_EOS'] and actual['actual_tensor_files_verified']
        expected.append({'case': n, 'folder': actual['folder'], 'request_id': actual['request_id'],
            'seal_sha256': actual['seal_sha256'], 'canonical_body_sha256': actual['body_sha256'],
            'original_body_file_sha256': plan[n]['original_body_sha256'],
            'wire_sha256': actual['wire_sha256'], 'native_text': actual['native_text']})
        selected[n] = actual, label
    raw, operation = remote('3090', 'EXPECTED=' + repr(expected) + '\n' + COMMON + BRIDGE,
                            'offline10-original-file-canonical-wire-reply-bridge')
    bridge = json.loads(raw)
    assert [v['case'] for v in bridge['rows']] == [v['case'] for v in new['rows']]
    source = PREP / 'package/native/native-parser-source.py'
    parse = next(n for n in ast.parse(source.read_text('utf8')).body
                 if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    env = {'re': re, 'json': json}
    exec(compile(ast.Module(body=[parse], type_ignores=[]), '<original-parser-only>', 'exec'), env)
    publications, rows = {}, []
    suffix = (PREP / 'package/proposed-system-suffix.txt').read_text('utf8')

    def restore(value):
        if isinstance(value, list):
            return [restore(v) for v in value]
        if isinstance(value, dict):
            if value.get('type') == 'image_url':
                data = (PACKETS / value['image_url']['url']).read_bytes()
                return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}}
            return {k: restore(v) for k, v in value.items() if k != 'review_projection_only'}
        return value

    for item in new['rows']:
        n = item['case']
        actual, label = selected[n]
        publication = Path(label['publication'])
        if publication not in publications:
            verify(publication)
            assert sha(publication / 'seal.json') == label['publication_seal_sha256']
            publications[publication] = load(publication / 'review-joined.json')
        published = next(v for v in publications[publication]['rows'] if v['candidate'] == n)
        assert hashlib.sha256(canonical(published)).hexdigest() == label['published_row_sha256']
        assert published['source_review_label'] is label['source_judgment']
        bound = published['execution_joins'][actual['run_id']]
        assert bound['request_id'] == actual['request_id'] and bound['request_seal_sha256'] == actual['seal_sha256']
        packet = load(PACKETS / ('packets/case-%02d.json' % n))
        body = restore(packet['legal_full_input_review_projection'])
        assert body['messages'][0]['content'].endswith('\n\n' + suffix)
        body['messages'][0]['content'] = body['messages'][0]['content'][:-len('\n\n' + suffix)]
        assert hashlib.sha256(canonical(body)).hexdigest() == actual['body_sha256']
        assert packet['input_tokens'] == actual['input_tokens'] + 292
        old_action = env['parse'](actual['native_text'])
        rows.append({'case': n, 'original_request_id': actual['request_id'],
            'original_request_seal_sha256': actual['seal_sha256'],
            'original_body_file_sha256': plan[n]['original_body_sha256'],
            'original_canonical_body_sha256': actual['body_sha256'],
            'original_source_publication': str(publication),
            'original_source_publication_seal_sha256': label['publication_seal_sha256'],
            'original_published_row_sha256': label['published_row_sha256'],
            'old_source_label_unchanged': label['source_judgment'],
            'new_source_label_unchanged': item['semantic_Mirage'],
            'new_source_row_sha256': hashlib.sha256(canonical(item)).hexdigest(),
            'old_candidate_exact_text': actual['native_text'],
            'new_candidate_exact_text': item['candidate_exact_text'],
            'same_exact_reply': actual['native_text'] == item['candidate_exact_text'],
            'old_native_action': old_action, 'new_native_action': item['native_action'],
            'same_native_action': old_action == item['native_action'],
            'new_proposed_action_executed': False, 'native_parser_valid': True,
            'old_positive_to_new_unresolved_not_counted_as_success': False})
    summary = load(AUDIT / 'summary.json')
    admission = load(AUDIT / 'admission.json')['result']
    result = {'time': time.time(), 'actual_postexit_audit': str(AUDIT), 'audit_seal_sha256': sha(AUDIT / 'seal.json'),
        'source_first_review': str(REVIEW), 'source_review_seal_sha256': sha(REVIEW / 'seal.json'),
        'narrow_metadata_bridge': bridge, 'bridge_operation': str(operation),
        'old_definite_positive_cases': [v['case'] for v in rows if v['old_source_label_unchanged'] is True],
        'new_definite_positive_cases': [v['case'] for v in rows if v['new_source_label_unchanged'] is True],
        'new_unresolved_cases': [v['case'] for v in rows if v['new_source_label_unchanged'] is None],
        'same_exact_reply_cases': [v['case'] for v in rows if v['same_exact_reply']],
        'same_native_action_cases': [v['case'] for v in rows if v['same_native_action']],
        'normal_plan_focus_footer_replies_preserved_cases': [1, 2, 44],
        'prose_native_direction_alignment_fixed_case': 20,
        'old_unsupported_STOP_replaced_by_unexecuted_back_case': 48,
        'persistent_exhaustive_exclusion_case': 43,
        'new_explicit_unsupported_exclusion_and_minimum_premise_case': 46,
        'all_ten_request_bodies_only_added_approved_system_suffix': True,
        'input_token_delta_per_case': 292, 'maximum_actual_input_tokens': 49451,
        'new_offline_model_calls': 10, 'natural_EOS_replies': 10, 'baseline_calls_replayed': 0,
        'new_GUI_Flash_scorer_paid_calls': 0, 'automatic_or_format_retries': 0,
        'all_ten_independent_frozen_prefixes_from_one_known_source_trajectory': True,
        'new_reply_never_inserted_in_later_prefix': True,
        'cannot_prove_reduced_first_occurrence_or_GUI_completion': True,
        'no_new_negative_WAIT_or_NO_recapture_semantic_validation': True,
        'unknown_not_negative': True, 'old_labels_and_new_sealed_labels_unchanged': True,
        'single_reviewer_nonblind': True, 'cost': summary,
        'cost_recorded_interval_scope': admission['reserved_seconds_scope'],
        'eight_GPU_interval_not_complete_holder_or_sealing_cost': True,
        'formal_changed_GUI_authorized': False, 'recommend_release_this_prompt_version': False,
        'effectiveness_proven': False, 'Mirage_reduction': None, 'goal': 'active', 'rows': rows}
    root = HERE / ('offline10-comparison-publication-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'comparison.json', result)
    report = root / '十条证据约束离线预检完整结果-20261115.md'
    lines = ['# 十条证据约束离线预检完整结果', '',
        '结论：本版未显示Mirage降低，不建议据此发布正式GUI。方向矛盾有局部修正，旧48号不再直接给出未经证明的最低价STOP；但43号的全体排除仍在，46号新增明确的错误历史前提。不能把更多探索当作已经降低触发率。', '',
        '用户批准的10个固定完整前缀全部完成：10次新27B调用、10个自然EOS，0格式或自动重试、0旧基线重跑、0GUI/Flash/评分/付费调用。保持原图、完整历史、原BF16/SDPA/seed42 greedy及每次2048输出；仅原system增加292个实际token，最长49451。新回复相互独立，后面的前缀仍是原历史，并不接收前一条新回复。', '',
        '289个实际退出后文件均核验，包括完整input IDs、pixels、grid、首次forward、原生生成参数、完整输出/EOS、每次归属与继承锁及事件链。全部模型与启动器实际退出；30张原1280×720图和完整合法历史先审，新回复标签在显式旧标签比较前已封存。单一审查者、已知来源非盲开发，不能当10个独立任务。', '',
        '| 固定前缀 | 旧回复Mirage | 新回复Mirage | 原生动作相同 |', '|---|---|---|---|']
    for row in rows:
        lines.append('| %d | %s | %s | %s |' % (row['case'], row['old_source_label_unchanged'],
                      row['new_source_label_unchanged'], row['same_native_action']))
    lines += ['', 'True为存在确定的证据越界断言，None为未决，False仅限该候选审查范围。固定集合中的确定阳性仍是2条：旧[43,48]，新[43,46]；这只是这10个选定前缀的描述性对照，不能换算整体触发率、显著性、独立样本或第一次错误减少。新17/29/47均未决，未转成阴性。', '',
        '20号：文字从scroll up变成scroll down，原生动作始终是down。它修正了表述与动作的一致性，原语义标签False不因此变成减少Mirage。', '',
        '43号：继续声称已检查全部12条900美元商品且无红把手，进而说最低价必在950组。合法历史对部分商品只提供小缩略图，Salsa原图可见红握把，不能靠旧叙述建立全体排除。任务中红把手是否包括握把、真正最便宜商品仍未决。', '',
        '46号：旧回复把950美元BMC称为仍需核对的候选；新回复额外断言“Since no $900 bike had red handlebars”和“the cheapest ... would be at $950”。这是新增的无充分来源支持的历史前提及最小值断言。随后说还要检查950组不删除已经发生的越界。BMC把带颜色的精确适配仍另列未决。', '',
        '48号：旧回复直接STOP并把950美元BMC宣称为最便宜；新回复仅描述当前Vanmoof并提议back继续检查。此候选避免了原STOP的过度结论，但动作未执行，不能证明任务能完成、探索有效或整条历史没有Mirage。', '',
        '1/2号计划和真实焦点、44号可读页脚及页2按钮仍有来源支持；这只是离线提议，不是新GUI正常操作或误拦率验证。新10条没有纯原生WAIT，也没有调用Flash，不提供新负例/WAIT或NO持续复拍的语义通过证据。', '',
        '成本：306940输入token、767输出token、724.18秒求和的原生模型调用时间。部署保留按8张3090记录，所记分配至子进程结束区间为7524.62 GPU秒；原0调用失败另保留795.26 GPU秒。二者未覆盖之后封存及原holder全部区间，不是完整成本、墙钟、货币、能耗或节省。', '',
        '两项本地汇总问题均单独保全：GUI技术中断与正常续跑共享run_id，已用真实request/Controller来源分开；比较脚本误把canonical JSON对象SHA同body文件SHA比较，已用原文件→对象→wire→回复的10条窄绑定修正。没有修改原终局、模型输入、语义标签或增加调用。', '',
        '下一步应先重新准备可复核的历史前提与全体排除检查及独立正常/负例/WAIT控制，再决定正式配对GUI条件。本版不自动进入正式GUI，授权10次已用完且不追加调用。Flash保持独立单图固定prompt的YES/NO，不接收主任务、候选或历史。总目标保持ACTIVE，尚未达到已证实防御有效。', '',
        '所有逐条回复、原生动作、来源SHA和审计指针见同目录comparison.json。', '']
    report.write_text('\n'.join(lines), encoding='utf8')
    archive = root / 'previous-heads'
    archive.mkdir()
    heads = [HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']
    original = {path: path.read_bytes() for path in heads}
    for i, path in enumerate(heads):
        (archive / ('%02d-%s' % (i, path.name))).write_bytes(original[path])
    for name in ['experiment-current.json', 'continuation-current.json', 'semantic-review-current.json']:
        path = HERE / name
        if path.exists():
            (archive / name).write_bytes(path.read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    state = {'publication': str(root), 'report': str(report), 'seal_sha256': sha(root / 'seal.json'),
             'new_source_review': str(REVIEW), 'actual_audit': str(AUDIT), 'goal': 'active',
             'effectiveness_proven': False, 'formal_changed_GUI_authorized': False}
    save(pointer, state)
    header = ('## 最新：29 GUI与10条批准离线均完成封存；本版没有证明降低Mirage\n\n'
        f'权威 {HERE.name}/{root.name}/comparison.json 与 {report.name}。批准10/10自然EOS，0重试/旧重跑/GUI/Flash/scorer/付费；289实际文件、完整input IDs/pixels/grid/首次forward/原参数/EOS/归属继承锁/事件链已退出后核验，模型与launcher实际退出。原system+292、最长49451、每次2048及全图全史/原精度种子不改，授权10次已用完，不追加或重开attempt。\n\n'
        '新源审先于显式旧标签join，30原PNG/完整合法历史已审；固定旧[43,48]与新[43,46]均2条确定阳性，17/29/47未决。20修正UP文字/DOWN动作矛盾、48改为未执行back探索，但43全体排除仍在、46新增无源900排除与950最低价前提；不称总体率/首次减少/完成率改善。旧发生与未决不抹去，单审已知来源开发不作独立任务。\n\n'
        '29GUI/520回复/14配对已在GUI29-completed-current.json发布：11完整trace相同、294 Flash全YES，0NO自然复拍。旧技术27公开回复/1未交付生成/全部原成本与0调用失败保留。新7524.62及旧795.26记录GPU秒均非完整holder/封存成本，主模型求和724.18秒非墙钟。\n\n'
        '所有旧终局、容量、父新fresh全量审计、批准10推理和postexit审计/导出/标签已完成，禁止重跑。比较metadata file/canonical SHA错误保全后以精确文件→对象→wire→回复窄绑定修正，原标签不改、0新增调用。正式新提示GUI未授权，本版不建议发布；下一步准备历史前提/排除检查与独立负例WAIT及具体取舍，再用户决定新条件。Flash原单图固定prompt/无主历史候选不变，目标ACTIVE。以下为历史。\n\n')
    for path in heads:
        assert path.read_bytes() == original[path]
        path.write_bytes(header.encode('utf8') + original[path])
    for name in ['experiment-current.json', 'continuation-current.json', 'semantic-review-current.json']:
        (HERE / name).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(root), 'report': str(report),
                      'old_positive': result['old_definite_positive_cases'],
                      'new_positive': result['new_definite_positive_cases'],
                      'unresolved': result['new_unresolved_cases'], 'effectiveness_proven': False,
                      'new_model_GUI_calls_by_publication': 0}))


if __name__ == '__main__':
    main()
