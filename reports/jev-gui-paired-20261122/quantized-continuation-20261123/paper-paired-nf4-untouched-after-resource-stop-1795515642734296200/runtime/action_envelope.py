"""Strict bridge for two observed Qwen action envelopes. No action inference."""
import hashlib
import json
import math
import re

VERSION = 'qwen-observed-action-envelopes-v1'
_WS = r'[ \t\r\n]*'
_TAG = re.compile(r'</?(?:action|tool_call|function|parameter)(?=[\s=>/]|$)', re.I)
_NOT_NATIVE = re.compile(r'</?(?:tool_call|function|parameter)(?=[\s=>/]|$)', re.I)
_NATIVE = re.compile(r'<action>\s*(.*?)\s*</action>', re.S)
_TOOL = re.compile(r'(?P<preamble>.*?)<tool_call>' + _WS +
                   r'<function=(?P<name>action|computer_use)>(?P<body>.*?)</function>' +
                   _WS + r'</tool_call>' + _WS, re.S)
_PARAM = re.compile(_WS + r'<parameter=(action|x|y)>([^<]*?)</parameter>', re.S)
_NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
_FIELDS = {'click': {'type', 'x', 'y'}, 'type': {'type', 'text'}, 'press': {'type', 'key'},
           'scroll': {'type', 'direction'}, 'back': {'type'}, 'wait': {'type'},
           'stop': {'type', 'answer'}, 'tab': {'type', 'index'}}


def _error():
    return ValueError('Unsupported or ambiguous Qwen action envelope')


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _error()
        out[key] = value
    return out


def _constant(_):
    raise _error()


def _json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def _typed(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('type'), str):
        raise _error()
    kind = payload['type']
    if _FIELDS.get(kind) != set(payload):
        raise _error()
    if kind == 'click':
        if any(type(payload[k]) not in (float, int) or not 0 < payload[k] < 1000 or not math.isfinite(payload[k])
               for k in ('x', 'y')):
            raise _error()
    if kind == 'tab' and (type(payload['index']) is not int or payload['index'] < 0):
        raise _error()
    if kind == 'scroll' and payload['direction'] not in ('up', 'down'):
        raise _error()
    for field in ('text', 'key', 'answer'):
        if field in payload and not isinstance(payload[field], str):
            raise _error()
    return payload


def _click_from_parameters(body):
    fields = {}
    cursor = 0
    while body[cursor:].strip():
        match = _PARAM.match(body, cursor)
        if match is None or match[1] in fields:
            raise _error()
        fields[match[1]] = match[2].strip(' \r\t\n')
        cursor = match.end()
    if set(fields) != {'action', 'x', 'y'} or fields['action'] != 'click':
        raise _error()
    if not all(_NUMBER.fullmatch(fields[k]) for k in ('x', 'y')):
        raise _error()
    # Keep the received numeric lexemes, then apply the same JSON parse as native.
    return '{"type":"click","x":' + fields['x'] + ',"y":' + fields['y'] + '}'


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def parse_model_reply(text, native_parse):
    """Pass ordinary replies unchanged; map exactly one complete observed alternative."""
    # A tool-like phrase inside an ordinary JSON argument is not a second envelope.
    if not _NOT_NATIVE.search(_NATIVE.sub('', text)):
        return native_parse(text), None
    match = _TOOL.fullmatch(text)
    if match is None or _TAG.search(match['preamble']):
        raise _error()
    body = match['body'].strip(' \r\t\n')
    if match['name'] == 'action':
        if _TAG.search(body):
            raise _error()
        native_json = body
        dialect = 'tool_call/function=action/JSON-object'
    else:
        native_json = _click_from_parameters(body)
        dialect = 'tool_call/function=computer_use/click/action-x-y'
    expected = _typed(_json(native_json))
    native_text = '<action>' + native_json + '</action>'
    payload = native_parse(native_text)
    if payload != expected:
        raise _error()
    return payload, {'version': VERSION, 'dialect': dialect, 'original_reply_sha256': _sha(text),
                     'function_body_sha256': _sha(body), 'parser_input_sha256': _sha(native_text),
                     'action_type': payload['type'], 'coordinates_rescaled': False,
                     'raw_reply_rewritten_or_replaced_in_history': False}
