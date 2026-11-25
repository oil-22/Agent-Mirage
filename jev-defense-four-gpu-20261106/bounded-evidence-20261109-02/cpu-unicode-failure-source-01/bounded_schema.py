"""Structural generation subset of the unchanged strict evidence validator."""
import hashlib
import json

def object_schema(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}

def string(maximum):return {'type':'string','minLength':1,'maxLength':maximum}
def enum(values):return {'type':'string','enum':values}
def array(items,maximum):return {'type':'array','items':items,'maxItems':maximum}

BOX={'type':'array','items':{'type':'integer','minimum':0,'maximum':1000},'minItems':4,'maxItems':4}
VISIBILITY=enum(['clear','partial','unknown'])
TEXT=object_schema({'id':enum(['t1','t2','t3','t4','t5','t6']),'text':string(160),'box_xyxy':BOX,'readability':VISIBILITY})
ELEMENT=object_schema({'id':enum(['e1','e2','e3','e4','e5','e6']),
    'kind':enum(['input','button','link','navigation','text','image','person','object','other','unknown']),
    'description':string(120),'box_xyxy':BOX,'text_refs':array(enum(['t1','t2','t3','t4','t5','t6']),6),'visibility':VISIBILITY})
SCHEMA=object_schema({'schema_version':enum(['image-evidence-v2-compact']),
    'coordinate_space':enum(['normalized_1000']),
    'frame':object_schema({'kind':enum(['gui','blank','explicit_loading','uninterpretable','non_gui','unknown']),
                          'summary':string(180),'limitations':array(string(160),2)}),
    'text_spans':array(TEXT,6),'elements':array(ELEMENT,6),
    'uncertain_regions':array(object_schema({'box_xyxy':BOX,'reason':string(120)}),2)})

def schema_sha256():
    return hashlib.sha256(json.dumps(SCHEMA,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def new_prefix_filter(tokenizer_data):
    from lmformatenforcer import JsonSchemaParser
    from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn
    return build_transformers_prefix_allowed_tokens_fn(tokenizer_data,JsonSchemaParser(SCHEMA))
