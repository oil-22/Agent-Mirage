"""Minimal LMFE bridge for native Transformers 5; no model/input modification.

The upstream optional Transformers integration imports a removed symbol. Keep
its vocabulary/decode algorithm, use the public TokenEnforcer directly.
"""
from functools import partial
import json

def decoded_text(tokenizer,tokens):
    # Matches lm_format_enforcer0.11.3's generic HF integration algorithm.
    return tokenizer.decode(tokens).rstrip('\ufffd')

def regular_tokens(tokenizer,vocab_size):
    zero=tokenizer.encode('0')[-1];rows=[];special=set(tokenizer.all_special_ids)
    for token in range(vocab_size):
        if token in special:continue
        after_zero=tokenizer.decode([zero,token])[1:]
        alone=tokenizer.decode([token])
        rows.append((token,after_zero,len(after_zero)>len(alone)))
    return rows

def build_token_data(tokenizer):
    from auxiliary_grammar_import import load_auxiliary_grammar
    api,_=load_auxiliary_grammar()
    TokenEnforcerTokenizerData=api.TokenEnforcerTokenizerData
    # Native tokenizer is ByteLevel. Preserve raw token bytes across incomplete
    # UTF-8 boundaries instead of decoding individual tokens to replacement chars.
    decoder=json.loads(tokenizer.backend_tokenizer.to_str())['decoder']
    if decoder['type']!='ByteLevel':raise ValueError('Unreviewed native tokenizer decoder')
    values=list(range(33,127))+list(range(161,173))+list(range(174,256))
    characters=list(values);extra=0
    for value in range(256):
        if value not in values:
            values.append(value);characters.append(256+extra);extra+=1
    inverse={chr(c):b for b,c in zip(values,characters)}
    raw={};special=set(tokenizer.all_special_ids);rows=[]
    for token in range(len(tokenizer)):
        if token in special:continue
        piece=tokenizer.convert_ids_to_tokens(token)
        raw[token]=bytes(inverse[c]for c in piece)
        rows.append((token,raw[token].decode('latin1'),False))
    def byte_prefix(ids):return b''.join(raw[token]for token in ids).decode('latin1')
    result=TokenEnforcerTokenizerData(rows,byte_prefix,tokenizer.eos_token_id,False,len(tokenizer))
    result.native_raw_token_bytes=raw
    return result

def byte_schema(schema):
    # Character-length enforcement is still performed by the UNCHANGED original
    # validator. The byte grammar allows up to four UTF-8 bytes per character;
    # this avoids imposing an ASCII-only/shorter-Unicode contract.
    if isinstance(schema,list):return[byte_schema(v)for v in schema]
    if not isinstance(schema,dict):return schema
    return{k:(v*4 if k=='maxLength'else byte_schema(v))for k,v in schema.items()}

class NativePrefixFilter:
    def __init__(self,tokenizer_data,parser):
        from auxiliary_grammar_import import load_auxiliary_grammar
        api,_=load_auxiliary_grammar()
        TokenEnforcer=api.TokenEnforcer
        self.enforcer=TokenEnforcer(tokenizer_data,parser)
    def __call__(self,batch_id,input_ids):
        if batch_id!=0:raise ValueError('Frozen single-input/no-beam condition required')
        return self.enforcer.get_allowed_tokens(input_ids.tolist()).allowed_tokens
