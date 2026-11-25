"""Replay exact sealed responses under the compatibility bridge, without inference or GUI."""
import ast
import hashlib
import json
import re
from pathlib import Path

from action_envelope import VERSION, parse_model_reply
from prepare import HERE, read, save, sha

REPAIR = HERE / 'action-envelope-repair'


def native_parser():
    pointer = read(HERE / 'frozen-current.json')
    p = Path(pointer['runtime'])
    original = p / 'native-parser-source.py'
    assert sha(original) == read(p / 'manifest.json')['files'][original.name]
    node, = [node for node in ast.parse(original.read_bytes()).body
             if isinstance(node, ast.FunctionDef) and node.name == 'parse']
    env = {'re': re, 'json': json}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(original), 'exec'), env)
    return env['parse'], sha(original)


def main():
    out = REPAIR / 'offline-qualification.json'
    assert not out.exists()
    replay = REPAIR / 'actual-early-failures.json'
    actual = read(replay)
    original, parser_hash = native_parser()
    expected = {146: {'type': 'click', 'x': 403, 'y': 567}, 155: {'type': 'click', 'x': 605, 'y': 419}}
    verified = []
    for h, row in actual['model']['result']['exact_distinct_replies_by_sha256'].items():
        text = row['text']
        assert hashlib.sha256(text.encode()).hexdigest() == h
        try:
            original(text)
        except ValueError as exc:
            assert str(exc) == 'Expected exactly one action JSON block'
        else:
            raise AssertionError('Expected native rejection preserved')
        payload, proof = parse_model_reply(text, original)
        assert payload == expected[row['task_id']] and proof['original_reply_sha256'] == h
        verified.append({'task_id': row['task_id'], 'exact_replies_exercised': 1, 'payload': payload, 'binding': proof})

    def tool(body, function='action'):
        return '<tool_call>\n<function=' + function + '>\n' + body + '\n</function>\n</tool_call>'

    def tags(items):
        return '\n'.join(f'<parameter={key}>\n{value}\n</parameter>' for key, value in items)

    click = '{"type":"click","x":4.03e2,"y":567}'
    tagged = tags([('action', 'click'), ('x', '403'), ('y', '567')])
    positives = {
        'native_click_unchanged': 'rooted evidence <action>' + click + '</action>',
        'native_literal_within_stop_argument': '<action>{"type":"stop","answer":"Saw & wrote <tool_call> literally"}</action>',
        'native_wait_unchanged': '<action>{"type":"wait"}</action>',
        'native_up_unchanged': '<action>{"type":"scroll","direction":"up"}</action>',
    }
    for name, text in positives.items():
        payload, proof = parse_model_reply(text, original)
        assert payload == original(text) and proof is None, name

    for text, payload in [
        (tool(click), {'type':'click','x':403.,'y':567}),
        (tool('{"type":"wait"}'), {'type':'wait'}),
        (tool('{"type":"type","text":"A  B \\uD83D\\uDD0D"}'), {'type':'type','text':'A  B 🔍'}),
        (tool('{"type":"stop","answer":"  a \\n b "}'), {'type':'stop','answer':'  a \n b '}),
        (tool(tagged, 'computer_use'), {'type':'click','x':403,'y':567}),
    ]:
        actual_payload, proof = parse_model_reply(text, original)
        assert actual_payload == payload and proof is not None

    rejects = {
        'two_tools': tool(click) + '\n' + tool(click),
        'mixed_native_and_tool': '<action>{"type":"wait"}</action>\n' + tool(click),
        'duplicate_action_key': tool('{"type":"click","type":"back","x":1,"y":2}'),
        'multiple_objects': tool(click + click),
        'reply_after_tool': tool(click) + '\nClick somewhere else',
        'partial_tool': tool(click).replace('</tool_call>', ''),
        'malformed_native_and_tool': '<action>\n' + tool(click),
        'bad_function': tool(click, 'browser'),
        'typo_opening': tool(click).replace('<tool_call>', '<tool_call >'),
        'wrong_direction': tool('{"type":"scroll","direction":"left"}'),
        'bool_coordinate': tool('{"type":"click","x":true,"y":2}'),
        'decoding_coercion': tool('{"type":"click","x":"403","y":2}'),
        'boundary_point': tool('{"type":"click","x":1000,"y":2}'),
        'nan': tool('{"type":"click","x":NaN,"y":2}'),
        'overflow': tool('{"type":"click","x":9e999,"y":2}'),
        'extra_field': tool('{"type":"click","x":4,"y":2,"target":"top"}'),
        'missing_stop_text': tool('{"type":"stop"}'),
        'negative_tab': tool('{"type":"tab","index":-1}'),
        'unicode_quotes_inside_type': tool('{"type":"type","text":"<action>"}'),
        'duplicate_parameter': tool(tagged + '\n' + tags([('x','403')]), 'computer_use'),
        'parameter_missing': tool(tags([('action','click'),('x','403')]), 'computer_use'),
        'parameter_array': tool(tagged.replace('403','[403,567]'), 'computer_use'),
        'parameter_alt_verb': tool(tagged.replace('\nclick\n','\nleft_click\n'), 'computer_use'),
        'parameter_scroll_unqualified': tool(tagged.replace('\nclick\n','\nscroll\n'), 'computer_use'),
        'no_action': 'The screenshot is readable, maybe click something.',
    }
    for name, text in rejects.items():
        try:
            parse_model_reply(text, original)
        except ValueError:
            pass
        else:
            raise AssertionError(f'should reject {name}')

    save(out, {'status': 'passed', 'version': VERSION, 'native_parser_sha256': parser_hash,
               'adapter_sha256': sha(HERE / 'action_envelope.py'), 'replay_receipt_sha256': sha(replay),
               'actual_20_v1_reply_bindings': len(actual['model']['result']['joined']),
               'actual_distinct': verified, 'native_unchanged_tests': list(positives),
               'strict_negative_tests': list(rejects), 'additional_positive_tests': 5,
               'new_model_GUI_scorer_calls': 0})
    print(json.dumps({'receipt': str(out), 'sha256': sha(out), 'negative_boundaries': len(rejects),
                      'distinct_real_early_replies_recovered_cpu': len(verified)}))


if __name__ == '__main__':
    main()
