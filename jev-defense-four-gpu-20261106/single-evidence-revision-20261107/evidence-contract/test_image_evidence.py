import copy
import io
import json
import unittest
from PIL import Image
from image_evidence import (EvidenceContractError, FIXED_PROMPT, actor_packet,
    build_image_only_request, decode_raw, validate_evidence, validate_image_only_request)


def example():
    return {'schema_version': 'image-evidence-v1', 'coordinate_space': 'normalized_1000',
        'frame': {'kind': 'gui', 'summary': 'A form and navigation are visible.',
                  'limitations': ['Tiny image details remain unresolved.']},
        'text_spans': [{'id': 't1', 'text': 'Next >', 'box_xyxy': [100, 200, 300, 250], 'readability': 'clear'}],
        'elements': [{'id': 'e1', 'kind': 'button', 'description': 'An outlined rectangular control.',
                      'box_xyxy': [90, 190, 310, 260], 'text_refs': ['t1'], 'visibility': 'clear'}],
        'uncertain_regions': [{'box_xyxy': [400, 200, 500, 300], 'reason': 'The small image is not clear enough.'}]}


class EvidenceBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = io.BytesIO(); Image.new('RGB', (1280, 720), 'white').save(output, format='PNG')
        cls.image = output.getvalue()

    def test_request_retains_original_bytes_and_has_no_agent_context_channel(self):
        request = build_image_only_request(self.image, 'fixed-development-model', 'a' * 40)
        self.assertEqual(validate_image_only_request(request), self.image)
        for extra in ('task', 'history', 'candidate', 'target', 'expected_label', 'injection'):
            bad = copy.deepcopy(request); bad[extra] = 'context'
            with self.subTest(field=extra), self.assertRaises(EvidenceContractError):
                validate_image_only_request(bad)

    def test_dynamic_prompt_and_image_or_size_substitution_rejected(self):
        request = build_image_only_request(self.image, 'fixed-development-model', 'a' * 40)
        for field, replacement in [('prompt', FIXED_PROMPT + 'Task-specific hint'),
                                   ('image_sha256', '0' * 64), ('original_size', [720, 1280])]:
            bad = copy.deepcopy(request); bad[field] = replacement
            with self.subTest(field=field), self.assertRaises(EvidenceContractError):
                validate_image_only_request(bad)

    def test_packet_is_fallible_and_does_not_certify_actions(self):
        request = build_image_only_request(self.image, 'fixed-development-model', 'a' * 40)
        packet = actor_packet(request, json.dumps(example()), True)
        self.assertFalse(packet['automatic_allow_or_block'])
        self.assertFalse(packet['semantic_correctness_established'])
        self.assertFalse(packet['inventory_is_exhaustive'])
        self.assertEqual(packet['auxiliary_model_count'], 1)

    def test_non_eos_is_never_a_valid_reply(self):
        request = build_image_only_request(self.image, 'fixed-development-model', 'a' * 40)
        with self.assertRaises(EvidenceContractError):
            actor_packet(request, json.dumps(example()), False)

    def test_bad_geometry_and_mixed_units_rejected_without_clamping(self):
        for box in ([0, 0, 1001, 200], [50, 50, 50, 100], [200, 10, 100, 20],
                    [0, 0, True, 100], [0.0, 0, 100, 100]):
            value = example(); value['text_spans'][0]['box_xyxy'] = box
            snapshot = copy.deepcopy(value)
            with self.subTest(box=box), self.assertRaises(EvidenceContractError):
                validate_evidence(value)
            self.assertEqual(value, snapshot)

    def test_duplicate_and_missing_evidence_ids_rejected(self):
        a = example(); a['elements'][0]['id'] = 't1'
        b = example(); b['elements'][0]['text_refs'] = ['absent']
        c = example(); c['elements'][0]['text_refs'] = ['t1', 't1']
        for value in (a, b, c):
            with self.assertRaises(EvidenceContractError):
                validate_evidence(value)

    def test_empty_inventory_and_uncertainty_are_legal(self):
        value = example(); value['frame']['kind'] = 'unknown'
        value['text_spans'] = []; value['elements'] = []
        self.assertEqual(validate_evidence(value), value)

    def test_json_duplicate_keys_markdown_extra_fields_and_nan_rejected(self):
        raw = json.dumps(example())
        cases = ['```json\n' + raw + '\n```', raw + raw,
                 raw.replace('"schema_version":', '"schema_version":"bad","schema_version":', 1),
                 raw[:-1] + ',"task_answer":"go"}', raw.replace('100, 200', 'NaN, 200', 1)]
        for value in cases:
            with self.assertRaises(EvidenceContractError):
                decode_raw(value)

    def test_invalid_enum_types_and_over_cap_inventory_rejected(self):
        a = example(); a['frame']['kind'] = []
        b = example(); b['elements'][0]['visibility'] = True
        c = example(); c['text_spans'] *= 17
        for value in (a, b, c):
            with self.assertRaises(EvidenceContractError):
                validate_evidence(value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
