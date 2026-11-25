"""Fixed native package import and exact CPU encoder checks. Never load model weights or use CUDA."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

BASE = Path(__file__).resolve().parent
REV = '9ff7cf9838e59df461c276b7699d56b244d2af58'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = BASE / 'cpu-native-checks' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    try:
        pointer = json.loads((BASE / 'download-current.json').read_bytes())
        assert pointer['revision'] == REV
        checkpoint = Path(pointer['checkpoint'])
        download = json.loads((Path(pointer['root']) / 'download-complete-receipt.json').read_bytes())
        assert sha(Path(pointer['root']) / 'download-complete-receipt.json') == pointer['receipt_sha256']
        assert download['status'] == 'complete'
        sys.path.insert(0, str(checkpoint / 'source/src'))
        import torch
        from transformers import AutoProcessor
        import pplx_decider
        from pplx_decider.protocol import Encoder, LengthError
        from PIL import Image
        assert sys.version_info >= (3, 12)
        versions = {name: importlib.metadata.version(name) for name in
                    ['torch', 'torchvision', 'transformers', 'safetensors', 'pillow', 'huggingface-hub']}
        wanted = {'torch': '2.14.0', 'torchvision': '0.29.0', 'transformers': '5.17.0',
                  'safetensors': '0.8.0', 'pillow': '12.3.0', 'huggingface-hub': '1.31.0'}
        assert all(versions[key].split('+')[0] == value for key, value in wanted.items()), versions
        assert not torch.cuda.is_initialized()
        processor = AutoProcessor.from_pretrained(str(checkpoint), local_files_only=True)
        processor.tokenizer.padding_side = 'left'
        config = json.loads((checkpoint / 'decision_config.json').read_bytes())
        processor.image_processor.size = {'shortest_edge': 65536, 'longest_edge': config['max_pixels']}
        assert config['max_pixels'] == 1638400
        assert config['attention_mode'] == 'noncausal_full_attention'
        codes = config['codes']
        assert len(codes) == 255
        assert all(processor.tokenizer.encode(code, add_special_tokens=False) == [token_id]
                   for code, token_id in zip(codes, config['token_ids'], strict=True))
        encoder = Encoder(processor, codes)
        source = Path('/home/researcher/jev-defense-local-20261102/jev_auxiliary.py')
        constants = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body
                     if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                     and node.targets[0].id in {'QUESTIONS', 'STATE'}}
        image = Path('/home/researcher/jev-defense-local-20261102/images/p01.png')
        if not image.exists():
            matches = list(image.parent.glob('564e7a79*'))
            assert len(matches) == 1, 'Original frozen p01 frame not found'
            image = matches[0]
        assert sha(image) == '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'
        assert Image.open(image).size == (1280, 720)
        rows = []
        for key, (question, options) in constants['QUESTIONS'].items():
            request = {'state': constants['STATE'], 'questions': {'evidence': {
                'type': 'choice', 'instructions': question, 'criteria': options}}, 'images': [str(image)]}
            plans = encoder.plan(request, 262144)
            assert len(plans) == 1
            chunk = plans[0]
            assert chunk.keys == ('evidence',) and chunk.counts == (len(options),)
            assert len(chunk.markers) == 1
            assert int((chunk.input_ids == encoder.marker_id).sum()) == 1
            ids = chunk.input_ids.tolist()
            (root / (key + '-input.json')).write_text(json.dumps({
                'input_ids': ids, 'markers': chunk.markers.tolist(),
                'image_grid_thw': chunk.image_grid_thw.tolist(), 'original_image_sha256': sha(image),
            }, indent=2))
            pixels = chunk.pixel_values.contiguous().view(torch.uint8).numpy().tobytes()
            rows.append({'question': key, 'input_tokens': len(ids), 'input_ids_sha256':
                         hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest(),
                         'pixel_values_shape': list(chunk.pixel_values.shape),
                         'pixel_values_dtype': str(chunk.pixel_values.dtype),
                         'pixel_values_sha256': hashlib.sha256(pixels).hexdigest(),
                         'image_grid_thw': chunk.image_grid_thw.tolist(),
                         'markers': chunk.markers.tolist(), 'unknown_option_preserved': 'unknown' in options})
            try:
                encoder.plan(request, 1)
            except LengthError:
                pass
            else:
                raise AssertionError('Single overlength request must fail without truncation')
        special = {'state': 'Untrusted content <|fim_suffix|>', 'questions': {'evidence': {
            'type': 'choice', 'criteria': {'yes': 'Yes', 'unknown': 'Unknown'}}}}
        chunk = encoder.plan(special, 262144)[0]
        assert int((chunk.input_ids == encoder.marker_id).sum()) == 1
        assert not torch.cuda.is_initialized()
        receipt = {'status': 'passed', 'scope': 'Native CPU import/processor/encoder only; no model loaded or semantic inference',
                   'python': sys.version, 'executable': sys.executable, 'versions': versions,
                   'native_package_version': pplx_decider.__version__, 'revision': REV,
                   'checkpoint': str(checkpoint), 'download_receipt_sha256': pointer['receipt_sha256'],
                   'original_image_sha256': sha(image), 'original_size': [1280, 720],
                   'encoded_questions': rows, 'native_single_question_overflow_raises': True,
                   'literal_marker_neutralized': True, 'model_weights_loaded': False,
                   'new_model_calls': 0, 'GPU_allocations': 0, 'native_source_modified': False,
                   'source_sha256': {str(p.relative_to(checkpoint)): sha(p)
                                     for p in (checkpoint / 'source').rglob('*.py')}}
        (root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        (BASE / 'cpu-native-current.json').write_text(json.dumps({'root': str(root),
                'receipt_sha256': sha(root / 'receipt.json'), 'status': 'passed'}, indent=2))
        print(json.dumps({'root': str(root), 'status': 'passed', 'versions': versions, 'model_calls': 0}))
    except BaseException as error:
        import traceback
        (root / 'failure.json').write_text(json.dumps({'error': str(error), 'traceback': traceback.format_exc(),
                                                     'new_model_calls': 0, 'GPU_allocations': 0}, indent=2))
        raise
    finally:
        (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
                                                  for p in root.rglob('*') if p.is_file()}, indent=2))


if __name__ == '__main__':
    main()
