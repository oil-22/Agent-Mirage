"""CPU-only native encoding of the frozen image-only three-category observer. No weights loaded."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True

BASE = Path(__file__).resolve().parent
CONTRACT_SHA = '98a3adb4ecb4939bb500603121e21587d454a99233ee14a32ddca8f68fa35054'
IMAGE_SHA = '62a9331cb203851add5ff565f4188342e7317e8b95dc33a98179f4e6550bc94d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = BASE / 'cpu-image-observer-checks' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    try:
        identity = json.loads((BASE / 'identity-current.json').read_bytes())
        identity_path = Path(identity['receipt'])
        assert sha(identity_path) == identity['receipt_sha256']
        checkpoint = Path(identity['checkpoint'])
        sys.path.insert(0, str(checkpoint / 'source/src'))
        import torch
        from transformers import AutoProcessor
        import pplx_decider
        from pplx_decider.protocol import Encoder, LengthError, left_pad
        from PIL import Image
        versions = {name: importlib.metadata.version(name) for name in
                    ['torch', 'torchvision', 'transformers', 'safetensors', 'pillow', 'huggingface-hub']}
        wanted = {'torch': '2.14.0', 'torchvision': '0.29.0', 'transformers': '5.17.0',
                  'safetensors': '0.8.0', 'pillow': '12.3.0', 'huggingface-hub': '1.31.0'}
        assert sys.version_info >= (3, 12)
        assert all(versions[key].split('+')[0] == value for key, value in wanted.items()), versions
        assert not torch.cuda.is_initialized()
        torch.set_num_threads(8)
        contract_file = BASE / 'cpu-inputs/observer-contract-98a3adb4.json'
        image_file = BASE / 'cpu-inputs/initial-62a9331c.png'
        assert sha(contract_file) == CONTRACT_SHA and sha(image_file) == IMAGE_SHA
        contract = json.loads(contract_file.read_bytes())
        assert list(contract) == ['state', 'questions']
        assert list(contract['questions']) == ['frame_appearance', 'visible_layout', 'text_readability']
        assert set(contract) == {'state', 'questions'}
        assert Image.open(image_file).size == (1280, 720)
        (root / 'original.png').write_bytes(image_file.read_bytes())
        (root / 'observer-contract.json').write_bytes(contract_file.read_bytes())
        request = {**contract, 'images': [str(image_file)]}
        processor = AutoProcessor.from_pretrained(str(checkpoint), local_files_only=True)
        processor.tokenizer.padding_side = 'left'
        config = json.loads((checkpoint / 'decision_config.json').read_bytes())
        assert config['max_pixels'] == 1638400
        processor.image_processor.size = {'shortest_edge': 65536, 'longest_edge': config['max_pixels']}
        encoder = Encoder(processor, config['codes'])
        assert len(config['codes']) == 255
        assert all(processor.tokenizer.encode(code, add_special_tokens=False) == [token_id]
                   for code, token_id in zip(config['codes'], config['token_ids'], strict=True))
        plans = encoder.plan(request, 262144)
        assert len(plans) == 1
        chunk = plans[0]
        assert chunk.keys == ('frame_appearance', 'visible_layout', 'text_readability')
        assert chunk.counts == (5, 6, 5)
        assert len(chunk.markers) == 3
        assert int((chunk.input_ids == encoder.marker_id).sum()) == 3
        inputs = left_pad([chunk], encoder.pad_id)
        tensors = {}
        for key, tensor in inputs.items():
            raw = tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
            tensors[key] = {'shape': list(tensor.shape), 'dtype': str(tensor.dtype),
                            'sha256_raw_tensor_bytes': hashlib.sha256(raw).hexdigest()}
        (root / 'input-ids.json').write_text(json.dumps(chunk.input_ids.tolist()))
        (root / 'markers-and-grid.json').write_text(json.dumps({'markers': chunk.markers.tolist(),
            'image_grid_thw': chunk.image_grid_thw.tolist(), 'question_keys': chunk.keys,
            'option_counts': chunk.counts}, indent=2))
        (root / 'native-rendered-messages.json').write_text(json.dumps(encoder.messages(request), indent=2))
        (root / 'native-request.json').write_text(json.dumps(request, ensure_ascii=False, separators=(',', ':')))
        try:
            encoder.plan(request, 1)
        except LengthError:
            overflow_rejected = True
        else:
            raise AssertionError('Native single overlength question must reject rather than truncate')
        assert not torch.cuda.is_initialized()
        receipt = {'status': 'passed', 'scope': 'Fixed native CPU import/processor/three-question joint encoder only',
                   'checkpoint': str(checkpoint), 'revision': identity['revision'],
                   'identity_receipt': str(identity_path), 'identity_receipt_sha256': identity['receipt_sha256'],
                   'native_package_source': str(Path(pplx_decider.__file__).resolve()),
                   'native_package_version': pplx_decider.__version__,
                   'python': sys.version, 'executable': sys.executable, 'versions': versions,
                   'observer_contract_sha256': CONTRACT_SHA, 'original_image_sha256': IMAGE_SHA,
                   'original_size': [1280, 720], 'joint_question_count': 3,
                   'input_tokens': chunk.length, 'sequences': len(plans),
                   'markers': chunk.markers.tolist(), 'question_keys': list(chunk.keys),
                   'option_counts': list(chunk.counts), 'image_grid_thw': chunk.image_grid_thw.tolist(),
                   'actual_native_forward_inputs_cpu': tensors,
                   'native_single_question_overflow_rejects_without_truncation': overflow_rejected,
                   'max_pixels_native_default': 1638400, 'fast_path': False,
                   'candidate_task_history_provided': False,
                   'native_source_modified': False, 'model_weights_loaded': False,
                   'model_forward_calls': 0, 'GPU_allocations': 0, 'semantic_pass': None,
                   'shared_question_attention_is_original_native_behavior': True}
        (root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        (BASE / 'cpu-image-observer-current.json').write_text(json.dumps({'root': str(root),
            'receipt_sha256': sha(root / 'receipt.json'), 'status': 'passed'}, indent=2))
        print(json.dumps({'root': str(root), 'status': 'passed', 'input_tokens': chunk.length,
                          'markers': chunk.markers.tolist(), 'model_calls': 0}))
    except BaseException:
        import traceback
        (root / 'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
                                                   for p in root.rglob('*') if p.is_file()}, indent=2))


if __name__ == '__main__':
    main()
