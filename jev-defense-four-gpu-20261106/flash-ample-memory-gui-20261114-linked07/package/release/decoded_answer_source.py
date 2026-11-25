"""Exact native-STOP-answer source mapping. Staged only; no truth/action decision."""
import copy
import hashlib
import json
import re


class UnboundAnswer(ValueError):
    pass


def _space(text, pos):
    while pos < len(text) and text[pos] in ' \t\n\r':
        pos += 1
    return pos


def _answer_token(candidate, native_payload):
    # This is the frozen native parser's block rule. The caller must supply its
    # actual parsed payload too; no alternative action is selected here.
    blocks = list(re.finditer(r'<action>\s*(.*?)\s*</action>', candidate, re.S))
    if len(blocks) != 1:
        raise UnboundAnswer('Not exactly one native action block')
    block = blocks[0].group(1)
    parsed = json.loads(block)
    if parsed != native_payload or not isinstance(parsed, dict):
        raise UnboundAnswer('Payload does not match original native parser')
    if parsed.get('type') != 'stop' or not isinstance(parsed.get('answer'), str):
        raise UnboundAnswer('Only an actual STOP answer has this source lane')
    decoder = json.JSONDecoder()
    pos = _space(block, 0)
    if pos >= len(block) or block[pos] != '{':
        raise UnboundAnswer('Action must be an object')
    pos += 1
    seen, found = set(), None
    while True:
        pos = _space(block, pos)
        if block[pos] == '}':
            pos += 1
            break
        key, end = decoder.raw_decode(block, pos)
        if not isinstance(key, str) or key in seen:
            raise UnboundAnswer('Ambiguous or duplicate top-level key')
        seen.add(key)
        pos = _space(block, end)
        if block[pos] != ':':
            raise UnboundAnswer('Missing colon')
        start = _space(block, pos + 1)
        value, end = decoder.raw_decode(block, start)
        if key == 'answer':
            found = (value, blocks[0].start(1) + start, blocks[0].start(1) + end)
        pos = _space(block, end)
        if block[pos] == ',':
            pos += 1
        elif block[pos] == '}':
            pos += 1
            break
        else:
            raise UnboundAnswer('Invalid object separator')
    if _space(block, pos) != len(block) or found is None or found[0] != parsed['answer']:
        raise UnboundAnswer('Incomplete answer source')
    return found


def answer_source(candidate, native_payload):
    decoded, left, right = _answer_token(candidate, native_payload)
    token = candidate[left:right]
    if not token.startswith('"') or not token.endswith('"'):
        raise UnboundAnswer('Answer is not a JSON string token')
    chars, spans = [], []
    pos = 1
    simple = {'"': '"', '\\': '\\', '/': '/', 'b': '\b', 'f': '\f',
              'n': '\n', 'r': '\r', 't': '\t'}
    while pos < len(token) - 1:
        start = pos
        if token[pos] != '\\':
            char = token[pos]
            pos += 1
        elif token[pos + 1] != 'u':
            char = simple[token[pos + 1]]
            pos += 2
        else:
            code = int(token[pos + 2:pos + 6], 16)
            pos += 6
            if 0xD800 <= code <= 0xDBFF:
                if token[pos:pos + 2] != '\\u':
                    raise UnboundAnswer('Unpaired high surrogate')
                low = int(token[pos + 2:pos + 6], 16)
                if not 0xDC00 <= low <= 0xDFFF:
                    raise UnboundAnswer('Unpaired high surrogate')
                code = 0x10000 + ((code - 0xD800) << 10) + low - 0xDC00
                pos += 6
            elif 0xDC00 <= code <= 0xDFFF:
                raise UnboundAnswer('Unpaired low surrogate')
            char = chr(code)
        chars.append(char)
        spans.append([left + start, left + pos])
    if ''.join(chars) != decoded or json.loads(token) != decoded:
        raise UnboundAnswer('Decoded source does not round-trip')
    return dict(value=decoded, raw_token_span=[left, right], character_spans=spans,
                source_candidate_sha256=hashlib.sha256(candidate.encode('utf8')).hexdigest())


def check_with_exact_answer_source(verdict, candidate, native_payload, original_check):
    """Keep raw-source matches; bind only exact decoded substrings for failures.

    The original quote checker runs on a provenance-only copy. The actual verdict,
    actor action and statuses are never edited. No image truth is certified here.
    """
    original = original_check(verdict, candidate)
    result = copy.deepcopy(original)
    result.update(policy='exact-raw-or-native-STOP-answer-source-STAGED-v1',
        original_byte_checker_result=original, decoded_answer_bindings=[],
        representation_only=True, semantic_truth_or_claim_completeness_established=False,
        actual_verdict_or_action_modified=False, deployed=False)
    if not original['reject']:
        return result
    try:
        source = answer_source(candidate, native_payload)
    except (ValueError, TypeError, KeyError, IndexError):
        return result
    provenance_copy = copy.deepcopy(verdict)
    bindings = []
    for error in original['errors']:
        if error['reason'] != 'claim_text_not_an_exact_candidate_span':
            continue
        index = error['claim_index']
        quote = verdict['claims'][index]['text']
        starts, offset = [], 0
        while True:
            at = source['value'].find(quote, offset)
            if at < 0:
                break
            starts.append(at)
            offset = at + 1
        if not starts:
            continue
        occurrences = []
        for at in starts:
            raw_left = source['character_spans'][at][0]
            raw_right = source['character_spans'][at + len(quote) - 1][1]
            raw = candidate[raw_left:raw_right]
            if json.loads('"' + raw + '"') != quote:
                raise UnboundAnswer('Substring did not round-trip')
            occurrences.append(dict(decoded_span=[at, at + len(quote)], raw_candidate_span=[raw_left, raw_right]))
        # All equivalent occurrences are retained. This first representation is
        # used only to invoke the original byte checker, not to choose a referent.
        first = occurrences[0]['raw_candidate_span']
        provenance_copy['claims'][index]['text'] = candidate[first[0]:first[1]]
        bindings.append(dict(claim_index=index, claim_id=verdict['claims'][index].get('id'),
            source='native_action.answer', quote_sha256=hashlib.sha256(quote.encode('utf8')).hexdigest(),
            raw_answer_token_span=source['raw_token_span'], occurrences=occurrences,
            unique_occurrence=len(occurrences) == 1))
    checked = original_check(provenance_copy, candidate)
    result.update(reject=checked['reject'], errors=checked['errors'],
        decoded_answer_bindings=bindings, original_byte_checker_on_provenance_copy=checked)
    return result
