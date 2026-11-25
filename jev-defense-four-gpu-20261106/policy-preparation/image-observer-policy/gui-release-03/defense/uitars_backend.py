"""Separate candidate verifier; inherits unchanged public serialization/grammar.

Not wired into the running27B service. Real-input preflight is required before use.
"""
import json
from pathlib import Path
from .core import digest
from .qwen_backend import LocalQwen

def verified_device_placement(model):
    """Verify actual parameters/buffers, including direct loads without Accelerate metadata."""
    declared=getattr(model,'hf_device_map',None)
    if declared is not None and any(str(v)in {'cpu','disk'}for v in declared.values()):
        raise RuntimeError('CPU/disk offload is outside the proposed BF16 comparison')
    devices=sorted({str(t.device)for t in list(model.parameters())+list(model.buffers())})
    if not devices or any(not d.startswith('cuda:')for d in devices):
        raise RuntimeError('Every verifier parameter and buffer must be on CUDA: '+str(devices))
    return ({k:str(v)for k,v in declared.items()}if declared is not None else {'':devices[0]}),devices,('hf_device_map_and_actual_tensors'if declared is not None else'actual_tensors_direct_load')

class LocalUITarsVerifier(LocalQwen):
    def __init__(self,model_path,runtime_path,max_memory_gib=20,placement='auto'):
        import torch,transformers
        from transformers import AutoProcessor,Qwen2_5_VLForConditionalGeneration
        self.torch=torch;root=Path(model_path)
        config=json.loads((root/'config.json').read_bytes())
        if config.get('model_type')!='qwen2_5_vl' or config.get('num_hidden_layers')!=28:
            raise ValueError('Unexpected UI-TARS candidate architecture; inspect provenance first')
        self.processor=AutoProcessor.from_pretrained(model_path,local_files_only=True)
        self.model=Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,dtype=torch.bfloat16,attn_implementation='sdpa',device_map=placement,
            max_memory={i:f'{max_memory_gib}GiB'for i in range(torch.cuda.device_count())},
            local_files_only=True).eval()
        device_map,actual_devices,placement_source=verified_device_placement(self.model)
        if placement=={'':0}and actual_devices!=['cuda:0']:
            raise RuntimeError('Explicit single-device preflight must use only logical CUDA0')
        if self.model.dtype!=torch.bfloat16:raise RuntimeError('Candidate verifier must load BF16')
        names=['config.json','generation_config.json','preprocessor_config.json','tokenizer_config.json','model.safetensors.index.json']
        self.runtime={'role':'verifier_only','model_candidate':'UI-TARS-1.5-7B',
            'model_path':str(root.resolve()),'class':type(self.model).__name__,
            'dtype':str(self.model.dtype),'backend':'sdpa',
            'device_map':device_map,'actual_tensor_devices':actual_devices,'placement_verification_source':placement_source,
            'torch':torch.__version__,'transformers':transformers.__version__,
            'metadata_sha256':{n:digest((root/n).read_bytes())for n in names if(root/n).exists()},
            'full_weight_sha_and_official_revision_verified_by_this_adapter':False,
            'history_truncation':False,'external_image_resizing':False,
            'processor':'candidate native processor defaults; record image-grid/input sizes during preflight',
            'judge_serialization_and_json_grammar':'inherited unchanged from LocalQwen',
            'ready_for_formal_trials':False,'requires_real_source_bound_preflight':True}
        Path(runtime_path).write_text(json.dumps(self.runtime,indent=2),encoding='utf8')

    def generate(self,messages,max_tokens,receipt,seed=42,original_body=None,json_schema=None):
        if original_body is not None:
            raise ValueError('UI-TARS candidate is verifier-only; original actor stays on27B')
        return super().generate(messages,max_tokens,receipt,seed=seed,
                                original_body=None,json_schema=json_schema)
