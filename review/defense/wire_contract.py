import base64,json,re
from .gate_core import canonical,digest
FIELDS={'request_id','image_png_base64','image_sha256'}
REVISION='9ff7cf9838e59df461c276b7699d56b244d2af58'

def decode_request(raw):
    def unique(pairs):
        value={}
        for k,v in pairs:
            if k in value:raise ValueError('Duplicate request field')
            value[k]=v
        return value
    v=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(v,dict) or set(v)!=FIELDS:raise ValueError('Only request ID and one image are accepted; no prompt/history/task/candidate')
    if not isinstance(v['request_id'],str) or not re.fullmatch('[0-9a-f]{32}',v['request_id']):raise ValueError('Invalid request ID')
    if not isinstance(v['image_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',v['image_sha256']):raise ValueError('Invalid image hash')
    image=base64.b64decode(v['image_png_base64'],validate=True)
    if not image.startswith(b'\x89PNG\r\n\x1a\n') or digest(image)!=v['image_sha256']:raise ValueError('Complete PNG/hash mismatch')
    return v,image

def native_request(contract,image):
    # No dynamic user state, extra questions, prior images or previous decisions.
    return {'state':contract['state'],'images':[image],'questions':{'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}}
