"""Supplement auxiliary byte grammar with decoded JSON character limits.

The existing byte grammar needs four-byte room for Unicode. This independent
filter counts the actual decoded code points, including JSON escapes and UTF8
fragments across token boundaries. It never edits a selected token or output.
The strict final schema/semantic validator is still mandatory. No main-model
module, logits, prompt, image, output cap or generation setting is changed.
"""
from dataclasses import dataclass, field
import json


class InvalidLengthPrefix(ValueError):
    pass


def field_limits(schema):
    found={}
    def walk(value, key=None):
        if not isinstance(value,dict):return
        if value.get('type')=='string' and 'maxLength'in value:
            maximum=value['maxLength']
            if key in found and found[key]!=maximum:
                raise ValueError('Ambiguous string field limit')
            found[key]=maximum
        for name,child in value.get('properties',{}).items():walk(child,name)
        if 'items'in value:walk(value['items'],key)
    walk(schema)
    return found


@dataclass
class LengthState:
    limits: dict
    stack: list=field(default_factory=list)
    in_string: bool=False
    is_key: bool=False
    key_raw: bytes=b''
    maximum: object=None
    count: int=0
    pending_high: bool=False
    escape: str=''
    hex_digits: str=''
    utf8_remaining: int=0
    next_minimum: int=0x80
    next_maximum: int=0xbf

    def clone(self):
        value=LengthState(self.limits)
        value.__dict__.update(self.__dict__)
        value.stack=[dict(row)for row in self.stack]
        return value

    def _scalar(self, unit=None):
        if unit is not None and 0xdc00<=unit<=0xdfff and self.pending_high:
            self.pending_high=False
            return
        self.count+=1
        self.pending_high=unit is not None and 0xd800<=unit<=0xdbff
        if self.maximum is not None and self.count>self.maximum:
            raise InvalidLengthPrefix('Decoded JSON string exceeds original character limit')

    def _current_field(self):
        if not self.stack:return None
        row=self.stack[-1]
        return row.get('key')if row['kind']=='object'else row.get('field')

    def feed(self, raw):
        """Accept a possibly incomplete UTF8/JSON token prefix or fail closed."""
        for byte in raw:
            if self.in_string:
                closing=(byte==34 and not self.escape and not self.utf8_remaining)
                if self.is_key and not closing:self.key_raw+=bytes([byte])
                if self.utf8_remaining:
                    if not self.next_minimum<=byte<=self.next_maximum:
                        raise InvalidLengthPrefix('Invalid UTF8 continuation')
                    self.utf8_remaining-=1
                    self.next_minimum,self.next_maximum=0x80,0xbf
                elif self.escape=='escape':
                    if byte==ord('u'):
                        self.escape='hex';self.hex_digits=''
                    elif byte in b'"\\/bfnrt':
                        self.escape='';self._scalar()
                    else:raise InvalidLengthPrefix('Invalid JSON escape')
                elif self.escape=='hex':
                    char=chr(byte)
                    if char not in '0123456789abcdefABCDEF':
                        raise InvalidLengthPrefix('Invalid JSON unicode escape')
                    self.hex_digits+=char
                    if self.maximum is not None and self.count==self.maximum:
                        # At the cap only completion of a surrogate pair can
                        # add an escape without increasing decoded len().
                        low=int(self.hex_digits,16)*16**(4-len(self.hex_digits))
                        high=low+16**(4-len(self.hex_digits))-1
                        if not self.pending_high or high<0xdc00 or low>0xdfff:
                            raise InvalidLengthPrefix('No length-valid Unicode escape completion')
                    if len(self.hex_digits)==4:
                        unit=int(self.hex_digits,16)
                        self.escape='';self.hex_digits='';self._scalar(unit)
                elif byte==34:
                    if self.is_key:
                        key=json.loads(b'"'+self.key_raw+b'"')
                        if not self.stack or self.stack[-1]['kind']!='object':
                            raise InvalidLengthPrefix('Unexpected object key')
                        self.stack[-1]['key']=key
                        self.stack[-1]['expect_key']=False
                    self.in_string=False;self.key_raw=b''
                elif byte==92:
                    if self.maximum is not None and self.count==self.maximum and not self.pending_high:
                        raise InvalidLengthPrefix('No room for another decoded character')
                    self.escape='escape'
                elif byte<32:
                    raise InvalidLengthPrefix('Unescaped control character')
                elif byte<128:
                    self._scalar()
                else:
                    if 0xc2<=byte<=0xdf:
                        self.utf8_remaining=1
                    elif 0xe0<=byte<=0xef:
                        self.utf8_remaining=2
                    elif 0xf0<=byte<=0xf4:
                        self.utf8_remaining=3
                    else:raise InvalidLengthPrefix('Invalid UTF8 leading byte')
                    self.next_minimum=0xa0 if byte==0xe0 else 0x90 if byte==0xf0 else 0x80
                    self.next_maximum=0x9f if byte==0xed else 0x8f if byte==0xf4 else 0xbf
                    # Reserve this one character now, while allowing its
                    # remaining bytes to arrive in later native tokens.
                    self._scalar()
                continue
            if byte==34:
                self.is_key=bool(self.stack and self.stack[-1]['kind']=='object' and self.stack[-1]['expect_key'])
                self.maximum=None if self.is_key else self.limits.get(self._current_field())
                self.in_string=True;self.key_raw=b'';self.count=0;self.pending_high=False
                self.escape='';self.hex_digits='';self.utf8_remaining=0
            elif byte==123:
                self.stack.append({'kind':'object','key':None,'expect_key':True})
            elif byte==91:
                self.stack.append({'kind':'array','field':self._current_field()})
            elif byte in [125,93]:
                expected='object'if byte==125 else'array'
                if not self.stack or self.stack[-1]['kind']!=expected:
                    raise InvalidLengthPrefix('Mismatched JSON container')
                self.stack.pop()
            elif byte==44 and self.stack and self.stack[-1]['kind']=='object':
                self.stack[-1]['expect_key']=True;self.stack[-1]['key']=None
            elif byte>=128:
                raise InvalidLengthPrefix('Non-ASCII outside a JSON string')
        return self

    def complete(self):
        return not self.in_string and not self.stack and not self.escape and not self.utf8_remaining


class UnicodeLengthPrefixFilter:
    """Subset-only wrapper around the original auxiliary token grammar."""
    def __init__(self, tokenizer_data, original_filter, schema):
        self.original_filter=original_filter
        self.data=tokenizer_data
        self.state=LengthState(field_limits(schema))
        self.prompt=None;self.generated=[];self.calls=0;self.filtered=0
        self.features={}
        for token,raw in tokenizer_data.native_raw_token_bytes.items():
            if any(byte<32 or byte in [34,92] for byte in raw):continue
            try:value=raw.decode('utf8',errors='strict')
            except UnicodeDecodeError:continue
            self.features[token]=len(value)

    def _allows(self, token):
        if token in self.data.eos_token_id:return self.state.complete()
        raw=self.data.native_raw_token_bytes.get(token)
        if raw is None:return False
        if (self.state.in_string and not self.state.is_key and not self.state.escape and
                not self.state.utf8_remaining and token in self.features):
            return self.state.maximum is None or self.state.count+self.features[token]<=self.state.maximum
        try:self.state.clone().feed(raw)
        except (InvalidLengthPrefix,ValueError,UnicodeError):return False
        return True

    def __call__(self,batch_id,input_ids):
        if batch_id!=0:raise ValueError('Only original single-input, no-beam auxiliary is supported')
        ids=input_ids.tolist()
        if self.prompt is None:self.prompt=list(ids)
        if ids[:len(self.prompt)]!=self.prompt:raise ValueError('Input prefix changed')
        generated=ids[len(self.prompt):]
        if generated[:len(self.generated)]!=self.generated:raise ValueError('Generation prefix changed')
        for token in generated[len(self.generated):]:
            if token in self.data.eos_token_id:raise ValueError('Unexpected call after EOS')
            self.state.feed(self.data.native_raw_token_bytes[token])
        self.generated=list(generated)
        original=list(self.original_filter(batch_id,input_ids))
        result=[token for token in original if self._allows(token)]
        self.calls+=1;self.filtered+=len(original)-len(result)
        if not result:raise InvalidLengthPrefix('No token satisfies both unchanged grammar and decoded length limits')
        return result
