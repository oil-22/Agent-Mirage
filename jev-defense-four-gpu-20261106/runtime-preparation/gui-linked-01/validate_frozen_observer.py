"""Validate already frozen observer wires with the exact runtime CPU admission."""
import base64
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parent
RUNTIME = BASE.parent
sys.path.insert(0, str(RUNTIME))
from four_gpu_contract import digest, validate_admission, validate_frozen_wire, validate_observation


def main():
    frozen = RUNTIME.parents[0] / 'policy-preparation/image-observer-policy/observer-preflight-frozen-01'
    plan = json.loads((frozen / 'plan.json').read_bytes())
    admission = json.loads((frozen / 'server-admission.json').read_bytes())
    contract = json.loads((frozen / 'observer-contract.json').read_bytes())
    allowed = validate_admission(admission)
    checked = []
    for row in plan['requests']:
        raw = (frozen / row['wire']).read_bytes()
        body = json.loads(raw)
        validate_frozen_wire(raw, body, allowed)
        validate_observation(body, contract)
        assert digest(raw) == row['wire_sha256']
        image = base64.b64decode(body['image_base64'], validate=True)
        assert digest(image) == row['image_sha256'] == body['image_sha256']
        assert list(body['questions']) == row['native_question_order']
        assert {k: list(v['criteria']) for k, v in body['questions'].items()} == row['native_option_order']
        for source in [row['source_binding'], *row['additional_source_bindings']]:
            assert Path(source['path']).read_bytes() == image
            assert digest(Path(source['source_receipt']).read_bytes()) == source['source_receipt_sha256']
        checked.append({'case_id': row['case_id'], 'wire_sha256': digest(raw),
                        'image_sha256': digest(image), 'question_order': list(body['questions'])})
    for name, expected in json.loads((frozen / 'seal.json').read_bytes()).items():
        assert digest((frozen / name).read_bytes()) == expected
    root = BASE / 'frozen-validation' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    result = {'frozen_root': str(frozen), 'mode': admission['mode'],
        'admission_sha256': digest((frozen / 'server-admission.json').read_bytes()),
        'contract_sha256': digest((frozen / 'observer-contract.json').read_bytes()),
        'validated_requests': len(checked), 'max_new_calls': admission['max_new_calls'],
        'checks': checked, 'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}
    (root / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    (root / 'seal.json').write_text(json.dumps({'receipt.json': digest((root / 'receipt.json').read_bytes()),
        'validator_source_sha256': digest(Path(__file__).read_bytes())}, indent=2), encoding='utf8')
    print(json.dumps({'root': str(root), **result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
