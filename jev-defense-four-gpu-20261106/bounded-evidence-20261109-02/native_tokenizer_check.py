"""CPU native tokenizer/schema boundary checks; no weights or CUDA allocation."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'grammar-vendor'),str(HERE)]
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'

def main():
    target=HERE/'CPU-tokenizer-result';target.mkdir(exist_ok=False);error=None;rows=[];started=time.time()
    try:
        import torch
        from transformers import AutoTokenizer
        from native_format_bridge import build_token_data
        from bounded_schema import new_prefix_filter,schema_sha256
        assert not torch.cuda.is_initialized()
        tokenizer=AutoTokenizer.from_pretrained('/home/researcher/models/Qwen3.5-9B',local_files_only=True,trust_remote_code=False)
        before=time.time();data=build_token_data(tokenizer);build=time.time()-before
        base={'schema_version':'image-evidence-v2-compact','coordinate_space':'normalized_1000',
              'frame':{'kind':'gui','summary':'A visible interface','limitations':[]},'text_spans':[],'elements':[],'uncertain_regions':[]}
        cases=[]
        for text in ['A visible menu','中文人物','1 – 12 of 50 listings','6" chair','path \\ label','symbol » and 👤']:
            v=json.loads(json.dumps(base));v['frame']['summary']=text;cases.append((text,v,True))
        v=json.loads(json.dumps(base));v['frame']['kind']='blank';cases.append(('blank',v,True))
        for n in [6,7]:
            v=json.loads(json.dumps(base));v['text_spans']=[{'id':'t'+str(i%6+1),'text':'Literal','box_xyxy':[1,1,2,2],'readability':'clear'}for i in range(n)]
            cases.append(('entry_count_'+str(n),v,n<=6))
        prompt=tokenizer.encode('CPU structural test only.',add_special_tokens=False)
        for name,value,expected in cases:
            text=json.dumps(value,ensure_ascii=False,separators=(',',':'));tokens=tokenizer.encode(text,add_special_tokens=False)
            assert tokenizer.decode(tokens,clean_up_tokenization_spaces=False)==text,'Lossy native tokenization roundtrip'
            allowed_fn=new_prefix_filter(data);prefix=list(prompt);accepted=True;rejected_at=None;counts=[]
            for index,token in enumerate(tokens):
                allowed=allowed_fn(0,torch.tensor(prefix));counts.append(len(allowed))
                if token not in allowed:
                    accepted=False;rejected_at=index;break
                prefix.append(token)
            if accepted:accepted=tokenizer.eos_token_id in allowed_fn(0,torch.tensor(prefix))
            row={'case':name,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'tokens':len(tokens),
                 'accepted':accepted,'expected':expected,'rejected_at':rejected_at,'steps_checked':len(counts),
                 'allowed_counts_sha256':hashlib.sha256(json.dumps(counts).encode()).hexdigest()}
            rows.append(row);assert accepted==expected,row
        assert not torch.cuda.is_initialized()
        receipt={'status':'passed','tokenizer_vocab':len(tokenizer),'tokenizer_eos':tokenizer.eos_token_id,
                 'vocabulary_build_seconds':build,'tokenizer_alphabet_length':len(data.tokenizer_alphabet),
                 'tokenizer_alphabet_sha256':hashlib.sha256(data.tokenizer_alphabet.encode()).hexdigest(),
                 'schema_sha256':schema_sha256(),'cases':rows,'weights_or_model_calls':0,'CUDA_initialized':False}
    except BaseException:
        error=traceback.format_exc();receipt={'status':'failed','error':error,'cases':rows,'weights_or_model_calls':0}
    receipt.update(started=started,ended=time.time())
    (target/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps(receipt,ensure_ascii=False));return 1 if error else 0

if __name__=='__main__':raise SystemExit(main())
