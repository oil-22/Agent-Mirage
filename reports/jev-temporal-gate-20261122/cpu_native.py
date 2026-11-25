"""Check ordered visual input on the pinned native CPU processor. No weights or inference."""

import hashlib
import json
import math
import os
from pathlib import Path
import sys

os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')

from temporal_request import QUESTION_ID, native_request


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')


def main():
    import torch
    from transformers import AutoProcessor
    import transformers
    from PIL import __version__ as pillow_version

    root = Path(__file__).resolve().parent
    plan_path = root / 'plan.json'
    plan = json.loads(plan_path.read_bytes())
    assert os.getuid() == 1033 and not torch.cuda.is_available() and not torch.cuda.is_initialized()
    assert torch.__version__.split('+')[0] == '2.14.0' and transformers.__version__ == '5.17.0'
    torch.set_num_threads(4)
    checkpoint = Path(plan['checkpoint'])
    for name, expected in plan['pinned_source_sha256'].items():
        assert sha((checkpoint / name).read_bytes()) == expected, name
    sys.path.insert(0, str(checkpoint / 'source/src'))
    from pplx_decider import protocol

    assert Path(protocol.__file__).resolve() == checkpoint / 'source/src/pplx_decider/protocol.py'
    config = json.loads((checkpoint / 'decision_config.json').read_bytes())
    assert config['max_pixels'] == 1638400 and config['attention_mode'] == 'noncausal_full_attention'
    processor = AutoProcessor.from_pretrained(str(checkpoint), local_files_only=True)
    processor.tokenizer.padding_side = 'left'
    processor.image_processor.size = {'shortest_edge': protocol.MIN_PIXELS, 'longest_edge': config['max_pixels']}
    encoder = protocol.Encoder(processor, config['codes'])
    assert all(processor.tokenizer.encode(code, add_special_tokens=False) == [ident]
               for code, ident in zip(config['codes'], config['token_ids'], strict=True))

    def tensor(x):
        return {'shape': list(x.shape), 'dtype': str(x.dtype),
                'sha256': sha(x.contiguous().view(torch.uint8).numpy().tobytes())}

    single, rows = {}, []
    for row in plan['cases']:
        identifiers = [row['previous_image_sha256'], row['candidate_image_sha256']]
        pngs = [(root / 'images' / (key + '.png')).read_bytes() for key in identifiers]
        assert [sha(raw) for raw in pngs] == identifiers
        request = native_request(pngs[0], row['executed_action'], pngs[1])
        (chunk,) = encoder.plan(request, 262144)
        assert chunk.keys == (QUESTION_ID,) and chunk.counts == (2,) and chunk.markers.numel() == 1
        assert list(request['questions'][QUESTION_ID]['criteria']) == ['YES', 'NO']
        prompt = encoder.text(request)
        assert prompt.count('<|image_pad|>') == 2
        for index, key in enumerate(identifiers):
            if key not in single:
                # One-image encodes are CPU pixel references only, not additional decisions.
                (one,) = encoder.plan({**request, 'images': [request['images'][index]]}, 262144)
                single[key] = (one.image_grid_thw[0], one.pixel_values)
        grids = chunk.image_grid_thw.tolist()
        assert len(grids) == 2
        patches = list(map(math.prod, grids))
        pixels = chunk.pixel_values.split(patches, dim=0)
        for i, key in enumerate(identifiers):
            grid, refs = single[key]
            assert torch.equal(chunk.image_grid_thw[i], grid) and torch.equal(pixels[i], refs), (row['case'], i)
        actual = protocol.left_pad([chunk], encoder.pad_id)
        visual_tokens = int((actual['input_ids'] == processor.image_token_id).sum())
        factor = processor.image_processor.merge_size ** 2
        assert visual_tokens == sum(patches) // factor == 1760
        rows.append({'case': row['case'], 'native_request_sha256': sha(canon(request)),
                     'ordered_images': identifiers, 'executed_action': row['executed_action'],
                     'sequences': 1, 'markers': chunk.markers.tolist(), 'input_tokens': chunk.length,
                     'visual_tokens': visual_tokens, 'image_grid_thw': grids,
                     'forward_inputs_if_run': {k: tensor(v) for k, v in actual.items()},
                     'ordered_pixel_slice_sha256': [tensor(p)['sha256'] for p in pixels]})
    assert not torch.cuda.is_initialized()
    print(json.dumps({'status': 'passed', 'plan_sha256': sha(plan_path.read_bytes()),
                      'torch': torch.__version__, 'transformers': transformers.__version__, 'pillow': pillow_version,
                      'revision': plan['revision'], 'unique_original_images': len(single), 'rows': rows,
                      'new_model_calls': 0, 'GPU_allocations': 0, 'native_weights_loaded': False,
                      'GUI_calls': 0, 'scope': 'Pinned original Flash CPU processor and one-question native encoding only'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
