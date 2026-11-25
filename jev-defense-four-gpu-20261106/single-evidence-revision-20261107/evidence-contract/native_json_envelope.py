"""Staged lossless native JSON transport decoder; never changes visual fields.

Not installed in the four-image GPU attempt. Its original raw-only failures
remain terminal. This development decoder accepts only raw JSON or one complete
explicit json fence; it then applies the SAME original strict evidence schema.
"""
import re
from image_evidence import EvidenceContractError,decode_raw,digest

FENCE=re.compile(r'(?P<prefix>[ \t\r\n]*```json[ \t]*\r?\n)(?P<body>[\s\S]*?)(?P<suffix>\r?\n```[ \t\r\n]*)\Z')

def decode_native_envelope(raw,natural_eos):
    if type(natural_eos)is not bool or not natural_eos:
        raise EvidenceContractError('A complete natural EOS is required before transport decoding')
    if not isinstance(raw,str):raise EvidenceContractError('Original native raw text required')
    match=FENCE.fullmatch(raw)
    if match:
        body=match.group('body');start,end=match.span('body');kind='one_complete_explicit_json_fence'
    else:
        body=raw;start,end=0,len(raw);kind='raw_json'
    # No field repair, JSON searching, truncation, code execution or coercion.
    reading=decode_raw(body)
    return {'reading':reading,'transport':{'kind':kind,'raw_output_sha256':digest(raw.encode('utf-8')),
        'body_utf8_sha256':digest(body.encode('utf-8')),'body_codepoint_range':[start,end],
        'body_utf8_byte_range':[len(raw[:start].encode('utf-8')),len(raw[:end].encode('utf-8'))],
        'removed_only_exact_envelope_characters':bool(match),'semantic_fields_modified':False,
        'original_strict_schema_unchanged':True,'natural_eos_required':True,
        'current_four_GPU_terminal_conditions_reclassified':False,
        'new_transport_condition_not_yet_deployed':True}}
