"""Typed local pipe encoding. No pickle, code execution or signing API."""
import base64
import json


def encode(value):
    import numpy as np
    from enum import Enum
    if type(value).__module__ == 'browser_env.utils' and type(value).__name__ == 'DetachedPage':
        return {'__native_DetachedPage__': {'url': value.url, 'content': value.content}}
    if isinstance(value, Enum):
        if type(value).__module__ != 'browser_env.actions' or type(value).__name__ != 'ActionTypes':
            raise TypeError('Undeclared native enumeration')
        return {'__native_ActionTypes__': int(value)}
    if isinstance(value, np.ndarray):
        return {'__native_array__': base64.b64encode(value.tobytes()).decode('ascii'),
                'dtype': value.dtype.str, 'shape': list(value.shape)}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, bytes):
        return {'__native_bytes__': base64.b64encode(value).decode('ascii')}
    if isinstance(value, tuple):
        return {'__native_tuple__': [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError('Native dictionaries require string keys')
        return {k: encode(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError('Undeclared native RPC type: ' + type(value).__name__)


def decode(value):
    import numpy as np
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {'__native_DetachedPage__'}:
        from browser_env.utils import DetachedPage
        fields = value['__native_DetachedPage__']
        if set(fields) != {'url', 'content'} or any(not isinstance(v, str) for v in fields.values()):
            raise ValueError('Invalid native detached-page metadata')
        return DetachedPage(**fields)
    if set(value) == {'__native_ActionTypes__'}:
        from browser_env.actions import ActionTypes
        return ActionTypes(value['__native_ActionTypes__'])
    if set(value) == {'__native_array__', 'dtype', 'shape'}:
        dtype = np.dtype(value['dtype'])
        if dtype.hasobject or not all(type(n) is int and 0 <= n <= 100000 for n in value['shape']):
            raise ValueError('Invalid native array metadata')
        raw = base64.b64decode(value['__native_array__'], validate=True)
        if len(raw) > 128 * 1024 ** 2:
            raise ValueError('Native array too large')
        return np.frombuffer(raw, dtype=dtype).reshape(value['shape']).copy()
    if set(value) == {'__native_bytes__'}:
        return base64.b64decode(value['__native_bytes__'], validate=True)
    if set(value) == {'__native_tuple__'}:
        return tuple(decode(v) for v in value['__native_tuple__'])
    return {k: decode(v) for k, v in value.items()}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate RPC field')
        result[key] = value
    return result


def dumps(value):
    return json.dumps(encode(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8') + b'\n'


def loads(raw):
    return decode(json.loads(raw, object_pairs_hook=unique))
