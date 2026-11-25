"""Non-destructive single-assistant-turn view of raw autoregressive captures."""
import json,pathlib
import numpy as np
from transformers import AutoTokenizer
PATHS={'qwen27':'/opt/whz/llms/Qwen3.8-27B','qwen9':'/home/researcher/models/Qwen3.5-9B','glm':'/home/researcher/models/GLM-4.6V-Flash-411bb4d77144'}
tokenizers={};stops={}
def setup(model):
    if model in stops:return
    path=pathlib.Path(PATHS[model]);tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True);tokenizers[model]=tokenizer
    gen=path/'generation_config.json';config=json.loads(gen.read_text()) if gen.exists() else json.loads((path/'config.json').read_text())
    eos=config.get('eos_token_id',config.get('text_config',{}).get('eos_token_id',[]));eos=[eos] if isinstance(eos,int) else list(eos)
    if tokenizer.eos_token_id is not None:eos.append(tokenizer.eos_token_id)
    stops[model]=set(eos)
def view(r,folder,model):
    setup(model);ids=r['output_ids'];length=next((i+1 for i,x in enumerate(ids) if x in stops[model]),len(ids));ended=bool(ids and ids[length-1] in stops[model]);r=dict(r)
    r.update(raw_output_tokens=len(ids),raw_eos_reached=r['eos_reached'],raw_truncated=r['truncated'],single_reply_tokens=length,discarded_after_reply_tokens=len(ids)-length,single_reply_stop_ids=sorted(stops[model]))
    if length<len(ids):
        r['output_ids']=ids[:length];r['output_tokens']=length;r['output']=tokenizers[model].decode(ids[:length],skip_special_tokens=True,clean_up_tokenization_spaces=False)
        artifact=np.load(folder/r.get('reused_from',r['id'])/'attention.npz');mass=artifact['mass'][:length]
        r['mass']=mass.mean(axis=(0,1,2)).tolist();r['first_query_mass']=mass[0].mean(axis=(0,1)).tolist()
        if 'source_mass' in artifact:r['source_mass']=artifact['source_mass'][:length].mean(axis=(0,1,2)).tolist()
    r['eos_reached']=ended;r['truncated']=not ended
    return r
