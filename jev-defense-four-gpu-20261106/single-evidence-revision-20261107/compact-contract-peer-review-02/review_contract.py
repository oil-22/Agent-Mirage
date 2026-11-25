"""Independent CPU boundary review, synthetic inputs only; source unchanged."""
from datetime import datetime, timezone
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
from PIL import Image

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
SOURCE = ROOT / 'compact-evidence-02' / 'image_evidence.py'
EXPECTED = '081caa2595440dd1f813efaa4f960a78cd095b8448353d65a11f464593140676'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')


def main():
    original = SOURCE.read_bytes()
    assert sha(original) == EXPECTED
    module = types.ModuleType('independent_compact_evidence_review')
    exec(compile(original, str(SOURCE), 'exec'), module.__dict__)
    results = []

    def check(name, action, rejects=False):
        try:
            value = action()
            if rejects:
                raise AssertionError('Unexpected acceptance')
        except module.EvidenceContractError as error:
            if not rejects:
                raise
            results.append({'name': name, 'passed': True, 'expected': 'contract_reject', 'message': str(error)})
        else:
            results.append({'name': name, 'passed': True, 'expected': 'accept_or_exact_assertion'})
            return value

    def evidence():
        return {
            'schema_version': 'image-evidence-v2-compact', 'coordinate_space': 'normalized_1000',
            'frame': {'kind': 'gui', 'summary': '界面 / café', 'limitations': []},
            'text_spans': [{'id': 't1', 'text': '保存 / café', 'box_xyxy': [0, 1, 1000, 999], 'readability': 'clear'}],
            'elements': [{'id': 'e1', 'kind': 'button', 'description': 'Visible label', 'box_xyxy': [1, 2, 1000, 1000], 'text_refs': ['t1'], 'visibility': 'clear'}],
            'uncertain_regions': [],
        }

    def encoded(value=None):
        return json.dumps(evidence() if value is None else value, ensure_ascii=False, separators=(',', ':'))

    def altered(path, value):
        result = evidence()
        target = result
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return result

    def decoded_equal(raw):
        reading, transport = module.decode_native_transport(raw)
        assert reading == evidence()
        assert transport['raw_output_sha256'] == sha(raw.encode())
        start, end = transport['body_codepoint_range']
        a, b = transport['body_utf8_byte_range']
        body = raw[start:end]
        assert raw.encode('utf-8')[a:b] == body.encode('utf-8')
        assert transport['body_utf8_sha256'] == sha(body.encode())
        assert transport['semantic_fields_modified'] is False
        assert transport['strict_compact_schema_applied'] is True
        assert reading == json.loads(body)
        return transport

    raw = encoded()
    for name, value in [
        ('raw_unicode', raw), ('raw_surrounding_whitespace', '\n\t' + raw + '\r\n'),
        ('fence_unicode', '```json\n' + raw + '\n```'),
        ('fence_crlf', '\r\n```json \t\r\n' + raw + '\r\n```\r\n'),
        ('fence_body_whitespace_preserved', '```json\n \t' + raw + '  \n```'),
    ]:
        check(name, lambda value=value: decoded_equal(value))
    for name, value in [
        ('two_fences', '```json\n' + raw + '\n```\n```json\n' + raw + '\n```'),
        ('preface', 'Explanation\n```json\n' + raw + '\n```'),
        ('postface', '```json\n' + raw + '\n```\nExplanation'),
        ('missing_closing_fence', '```json\n' + raw),
        ('fence_without_explicit_language', '```\n' + raw + '\n```'),
        ('uppercase_fence_language', '```JSON\n' + raw + '\n```'),
        ('second_json_object', raw + '\n' + raw),
        ('trailing_nonjson', raw + 'DONE'), ('top_level_array', '[' + raw + ']'),
        ('top_level_null', 'null'), ('non_string_output', raw.encode()),
        ('nested_duplicate_key', raw.replace('"kind":"gui"', '"kind":"gui","kind":"blank"')),
        ('nan_constant', raw.replace('"summary":"界面 / café"', '"summary":NaN')),
        ('infinity_constant', raw.replace('"summary":"界面 / café"', '"summary":Infinity')),
    ]:
        check(name, lambda value=value: module.decode_raw(value), rejects=True)

    levels = [('top', []), ('frame', ['frame']), ('text', ['text_spans', 0]), ('element', ['elements', 0])]
    for name, path in levels:
        for operation in ('extra', 'missing'):
            value = evidence()
            target = value
            for key in path:
                target = target[key]
            if operation == 'extra':
                target['task'] = 'forbidden extra'
            else:
                del target[next(iter(target))]
            check(name + '_' + operation + '_field', lambda value=value: module.validate_evidence(value), rejects=True)

    for path, maximum, name in [
        (['frame', 'summary'], 180, 'summary'), (['text_spans', 0, 'text'], 160, 'literal'),
        (['elements', 0, 'description'], 120, 'element_description')
    ]:
        check(name + '_exact_length', lambda path=path, maximum=maximum: module.validate_evidence(altered(path, 'x' * maximum)))
        check(name + '_over_length', lambda path=path, maximum=maximum: module.validate_evidence(altered(path, 'x' * (maximum + 1))), rejects=True)
        check(name + '_blank', lambda path=path: module.validate_evidence(altered(path, '  ')), rejects=True)

    for name, path, bad in [
        ('wrong_schema', ['schema_version'], 'image-evidence-v1'), ('wrong_coordinates', ['coordinate_space'], 'pixels'),
        ('bad_frame_kind', ['frame', 'kind'], 'loading_probably'), ('bad_readability', ['text_spans', 0, 'readability'], 'certain'),
        ('bad_element_kind', ['elements', 0, 'kind'], 'action'), ('bad_visibility', ['elements', 0, 'visibility'], 'hidden'),
        ('duplicate_global_id', ['elements', 0, 'id'], 't1'), ('missing_text_ref', ['elements', 0, 'text_refs'], ['missing']),
        ('duplicate_text_ref', ['elements', 0, 'text_refs'], ['t1', 't1']),
        ('bool_coordinate', ['elements', 0, 'box_xyxy'], [False, 0, 10, 10]),
        ('float_coordinate', ['elements', 0, 'box_xyxy'], [0.0, 0, 10, 10]),
        ('inverted_coordinate', ['elements', 0, 'box_xyxy'], [10, 0, 0, 10]),
        ('zero_area_box', ['elements', 0, 'box_xyxy'], [0, 0, 0, 10]),
        ('negative_coordinate', ['elements', 0, 'box_xyxy'], [-1, 0, 10, 10]),
        ('outside_coordinate', ['elements', 0, 'box_xyxy'], [0, 0, 1001, 10]),
    ]:
        check(name, lambda path=path, bad=bad: module.validate_evidence(altered(path, bad)), rejects=True)

    for count in (6, 7):
        value = evidence()
        value['text_spans'] = [dict(copy.deepcopy(value['text_spans'][0]), id='t' + str(i)) for i in range(count)]
        value['elements'][0]['text_refs'] = []
        check('text_span_count_' + str(count), lambda value=value: module.validate_evidence(value), rejects=count > 6)
        value = evidence()
        value['elements'] = [dict(copy.deepcopy(value['elements'][0]), id='e' + str(i)) for i in range(count)]
        check('element_count_' + str(count), lambda value=value: module.validate_evidence(value), rejects=count > 6)
    for count in (2, 3):
        value = evidence()
        value['uncertain_regions'] = [{'box_xyxy': [1, 1, 2, 2], 'reason': 'Local unreadable pixels'} for _ in range(count)]
        check('uncertain_count_' + str(count), lambda value=value: module.validate_evidence(value), rejects=count > 2)
        value = evidence()
        value['frame']['limitations'] = ['Local caveat'] * count
        check('limitations_count_' + str(count), lambda value=value: module.validate_evidence(value), rejects=count > 2)
    for name, field, count in [('limitation', 'limitations', 160)]:
        for length in (count, count + 1):
            value = evidence()
            value['frame'][field] = ['x' * length]
            check(name + '_length_' + str(length), lambda value=value: module.validate_evidence(value), rejects=length > count)
    for length in (120, 121):
        value = evidence()
        value['uncertain_regions'] = [{'box_xyxy': [0, 0, 1, 1], 'reason': 'x' * length}]
        check('uncertainty_reason_length_' + str(length), lambda value=value: module.validate_evidence(value), rejects=length > 120)
    empty = evidence()
    empty['text_spans'] = []; empty['elements'] = []
    check('empty_nonexhaustive_inventories', lambda: module.validate_evidence(empty))
    value = evidence()
    validated = module.validate_evidence(value)
    validated['frame']['summary'] = 'changed copy'
    check('validated_reading_is_deep_copy', lambda: value['frame']['summary'] == '界面 / café' or (_ for _ in ()).throw(AssertionError('Source mutated')))

    image_buffer = io.BytesIO()
    Image.new('RGB', (2, 3), 'white').save(image_buffer, format='PNG')
    image_raw = image_buffer.getvalue()
    request = module.build_image_only_request(image_raw, 'fixed-model-for-test', 'fixed-revision-for-test')
    check('request_round_trip', lambda: module.validate_image_only_request(request) == image_raw or (_ for _ in ()).throw(AssertionError('Image changed')))
    for name in ('task', 'history', 'candidate', 'target', 'private_labels'):
        altered_request = dict(request, **{name: 'must not reach native request'})
        check('request_rejects_' + name, lambda altered_request=altered_request: module.validate_image_only_request(altered_request), rejects=True)
    for field, value in [('prompt', request['prompt'] + ' task'), ('image_sha256', '0' * 64), ('prompt_sha256', '0' * 64), ('original_size', [3, 2]), ('image_base64', request['image_base64'] + '!')]:
        altered_request = dict(request, **{field: value})
        check('request_tamper_' + field, lambda altered_request=altered_request: module.validate_image_only_request(altered_request), rejects=True)
    for value in (False, 0, 1, None, 'true'):
        check('actor_rejects_nonboolEOS_' + repr(value), lambda value=value: module.actor_packet(request, raw, value), rejects=True)
    def packet_exact():
        fenced = '```json\n' + raw + '\n```'
        packet = module.actor_packet(request, fenced, True)
        assert packet['reading'] == evidence()
        assert packet['image_sha256'] == sha(image_raw)
        assert packet['prompt_sha256'] == sha(module.FIXED_PROMPT.encode())
        assert packet['raw_output_sha256'] == sha(fenced.encode()) == packet['native_transport']['raw_output_sha256']
        assert packet['inventory_is_exhaustive'] is False
        assert packet['semantic_correctness_established'] is False
        assert packet['automatic_allow_or_block'] is False
        assert packet['image_freshness_known'] is False
        assert packet['auxiliary_model_count'] == 1
        assert packet['model'] == request['model'] and packet['revision'] == request['revision']
        assert packet['original_size'] == [2, 3]
    check('actor_packet_original_raw_and_request_provenance', packet_exact)
    check('actor_packet_rejects_invalid_reply', lambda: module.actor_packet(request, '{}', True), rejects=True)

    float_request = copy.deepcopy(request)
    float_request['original_size'] = [2.0, 3.0]
    float_accepted = module.validate_image_only_request(float_request) == image_raw
    check('document_float_dimensions_characterization', lambda: float_accepted or (_ for _ in ()).throw(AssertionError('Behavior changed')))
    assert SOURCE.read_bytes() == original
    receipt = {
        'status': 'independent_cpu_contract_review_complete',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_path': str(SOURCE), 'source_sha256_before': EXPECTED, 'source_sha256_after': sha(SOURCE.read_bytes()),
        'checks_passed': len(results), 'checks_failed': 0, 'results': results,
        'observations': [{
            'id': 'REQUEST_SIZE_TYPE_EQUIVALENCE', 'severity': 'low_boundary_gap_not_normal_builder_path',
            'fact': 'validate_image_only_request accepts original_size=[2.0,3.0] for a 2x3 source because Python dict/list equality equates integral floats and integers.',
            'impact': 'Image bytes/hash and actual numeric dimensions remain bound; exact request-field types are not fully enforced. Normal build_image_only_request emits integer sizes.',
            'recommended_disposition': 'Record limitation or require exact list-of-int dimensions before exposing validation to arbitrary external requests; a source change would need a new frozen SHA and tests.',
        }],
        'scope_limits': [
            'Model/revision metadata and natural EOS are caller assertions here; actual loaded weights, native forward IDs/pixels/grid, token EOS and response binding require worker/terminal receipts.',
            'Strict shape does not prove text accuracy, tight boxes, causal visibility explanations, exhaustive coverage or reduced Mirage.',
            'No task/history/candidate/private-label fields can be added to the fixed image-only request. This module does not prove a caller never sends context through a separate channel.',
            '6+6+2 and short strings reduce available evidence; omission cannot be converted into absence.',
            'This review never read model predictions, ran models, accessed servers, changed source or started GUI/actor/scorer.',
        ],
        'independent_subreview': {
            'reviewer': '/root/audit_three_structure/compact_contract_static', 'checks_passed': 13,
            'summary': 'Independent Unicode/CRLF/range/hash, fence and strict-schema boundary checks passed; no in-module context leak found.',
            'reported_tool_wrapper_failure': 'One initial tool JS template had a backtick SyntaxError before Python execution; rerun with a plain string succeeded, with no source/result mutation.',
        },
    }
    write_new('receipt.json', receipt)
    report = '''# Compact image-only contract independent review

The frozen source passed {checks} independent CPU boundaries, plus 13 separately checked transport/schema boundaries. It preserves raw output and body hashes/ranges, rejects incomplete or multiple transports, extra fields and duplicate keys, and retains strict EOS and fallible/nonexhaustive packet boundaries.

One low-risk type gap remains: the request rebuild comparison accepts integral floating-point `original_size` values. Original image bytes, SHA and numeric dimensions are still bound, and the ordinary builder emits integers. This is not a demonstrated inference corruption, but request field types should not be described as completely strict.

Actual loaded model/revision, forward IDs/pixels/grid, genuine EOS and cross-request response binding must still be verified from worker and terminal receipts. The module cannot establish visual correctness or defense efficacy. No prediction, remote endpoint, GPU, GUI or scorer was accessed.
'''.format(checks=len(results))
    write_new('独立CPU契约审查.md', report)
    entries = []
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            data = path.read_bytes()
            entries.append({'path': path.name, 'bytes': len(data), 'sha256': sha(data)})
    write_new('seal.json', {'status': 'independent_review_sealed', 'source_sha256': EXPECTED, 'entries': entries, 'entries_canonical_sha256': sha(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())})
    print(json.dumps({'checks_passed': len(results), 'receipt_sha256': sha((OUT/'receipt.json').read_bytes()), 'seal_sha256': sha((OUT/'seal.json').read_bytes()), 'source_sha256': EXPECTED, 'float_size_gap_reproduced': float_accepted}))


if __name__ == '__main__':
    main()
