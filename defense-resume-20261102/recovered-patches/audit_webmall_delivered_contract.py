"""Local-only audit of the delivered action list, not another source freeze."""
import ast
import hashlib
import json
import sys
import time
import types
from pathlib import Path

from webmall_delivered_action_contract import extract_contract, bind_parsed_call

BASE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    previous_path = BASE / 'webmall-delivered-contract-current.json'
    previous = json.loads(previous_path.read_bytes()) if previous_path.exists() else None
    source_pointer = json.loads((BASE / 'webmall-native-contract-source-current.json').read_bytes())
    source = Path(source_pointer['directory'])
    raw = (source / 'source-manifest.json').read_bytes()
    assert sha(raw) == source_pointer['manifest_sha256']
    manifest = json.loads(raw)
    for row in manifest['files']:
        assert sha((source / row['local']).read_bytes()) == row['sha256']
    parent_pointer = json.loads((BASE / 'webmall-native-contract-current.json').read_bytes())
    parent = Path(parent_pointer['directory'])
    assert sha((parent / 'contract-audit.json').read_bytes()) == parent_pointer['audit_sha256']
    parent_data = json.loads((parent / 'contract-audit.json').read_bytes())
    function_source = next(row for row in parent_data['supplemental_sources']
                           if row['local'].endswith('/functions.py'))
    function_bytes = (parent / 'source' / function_source['local']).read_bytes()
    assert sha(function_bytes) == function_source['sha256']
    native_functions = {n.name: n for n in ast.parse(function_bytes).body if isinstance(n, ast.FunctionDef)}
    parser = source / 'source/Browsergym/browsergym/core/src/browsergym/core/action/parsers.py'
    parser_tree = ast.parse(parser.read_bytes())
    assert {n.name for n in ast.walk(parser_tree) if isinstance(n, ast.alias)} == {
        'ast', 'pyparsing', 'dataclass', 'Any'}
    module = types.ModuleType('_webmall_delivered_native_parser')
    sys.modules[module.__name__] = module
    exec(compile(parser_tree, str(parser), 'exec'), module.__dict__)

    def bind(text, contract, strict):
        native = module.highlevel_action_parser
        if strict:
            calls = native.parse_string(text, parse_all=True).as_list()
        else:
            calls = sum(native.search_string(text).as_list(), [])
        if len(calls) != 1:
            raise ValueError('Exactly one parsed native action is required')
        name, args = calls[0]
        return bind_parsed_call(contract, name, args, module.NamedArgument)

    records = [json.loads(line) for line in (source / 'archive/agent_visible_trace.jsonl').read_text(encoding='utf-8').splitlines()]
    audit, contracts, source_matches = [], {}, {}
    for row in records:
        item = {'step': row['step'], 'action': row['action'],
                'action_json_sha256': sha(json.dumps(row['action'], ensure_ascii=False).encode())}
        try:
            contract = extract_contract(row['request_before_handoff_with_images_hashed'])
        except Exception as exc:
            item['contract_available'] = False
            item['error'] = type(exc).__name__ + ': ' + str(exc)
        else:
            item.update(contract_available=True, section_sha256=contract['section_sha256'],
                        source_block_sha256=contract['source_block_sha256'],
                        advertised_action_count=len(contract['signatures']))
            contracts[contract['section_sha256']] = {
                'section': contract['section'], 'single_action': True,
                'signatures': {k: {'native_header': v['native_header'],
                                   'argument_ast': v['argument_ast']}
                               for k, v in contract['signatures'].items()}}
            for name, data in contract['signatures'].items():
                actual = native_functions[name].args
                # Parameter names/defaults only; no runtime type enforcement is added.
                actual_shape = ([n.arg for n in actual.args],
                                [ast.dump(n, include_attributes=False) for n in actual.defaults])
                advertised = ast.parse('def ' + data['native_header'] + ':\n    pass').body[0].args
                advertised_shape = ([n.arg for n in advertised.args],
                                    [ast.dump(n, include_attributes=False) for n in advertised.defaults])
                source_matches[name] = actual_shape == advertised_shape
            if row['action'] is None:
                item['empty_terminal_record'] = True
            else:
                for strict in (False, True):
                    mode = 'strict_full_parse' if strict else 'native_search_parse'
                    try:
                        item[mode] = {'bound': True, 'binding': bind(row['action'], contract, strict)}
                    except Exception as exc:
                        item[mode] = {'bound': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        audit.append(item)
    first = extract_contract(records[0]['request_before_handoff_with_images_hashed'])
    # Regression for the original extraction bug: history calls must not be
    # counted among the declarations in the following Action space section.
    import copy
    history_fixture = copy.deepcopy(records[0]['request_before_handoff_with_images_hashed'])
    for message in history_fixture:
        if message.get('role') == 'user' and isinstance(message['content'], list):
            for block in message['content']:
                if block.get('type') == 'text' and '# Action space:' in block['text']:
                    block['text'] = "# History:\ngoto('http://localhost:8081')\nclick('42')\n" + block['text']
    with_history = extract_contract(history_fixture)
    assert first['section_sha256'] == with_history['section_sha256']
    assert first['source_block_sha256'] != with_history['source_block_sha256']
    examples = [
        ('native_click', "click('42')", True),
        ('native_fill', "fill('42', 'text')", True),
        ('native_named_navigation', "goto(url='http://localhost:8081')", True),
        ('native_named_tab', 'tab_focus(index=1)', True),
        ('native_noop_duration', 'noop(100)', True),
        ('missing_click_target', 'click()', False),
        ('missing_fill_value', "fill('42')", False),
        ('duplicate_target', "click('42', bid='43')", False),
        ('duplicate_named_target', "click(bid='42', bid='43')", False),
        ('unknown_keyword', "click('42', force=True)", False),
        ('excess_arguments', "fill('42', 'text', 'extra')", False),
        ('missing_scroll_component', 'scroll(0)', False),
        ('union_only_action_not_delivered', 'mouse_click(1, 2)', False),
        ('bare_wait_not_native', 'WAIT', False),
        ('two_native_actions', "click('42')\nclick('43')", False),
    ]
    controls = []
    for name, text, expected in examples:
        try:
            value = bind(text, first, False)
            observed, error = True, None
        except Exception as exc:
            value, observed, error = None, False, type(exc).__name__ + ': ' + str(exc)
        controls.append({'name': name, 'input': text, 'expected_binding': expected,
                         'bound': observed, 'matches': expected == observed,
                         'result': value, 'error': error})
    assert all(row['matches'] for row in controls)
    assert all(source_matches.values())
    out = BASE / 'native-adapter-sources' / ('webmall-delivered-contract-' + str(time.time_ns()))
    out.mkdir(exist_ok=False)
    data = {
        'source_manifest_sha256': source_pointer['manifest_sha256'],
        'previous_delivered_audit_preserved': previous,
        'repair_scope': 'Only source-section extraction: exclude preceding history from declaration scan. Inputs, actions, native parser, source functions and budgets unchanged.',
        'parent_audit_sha256': parent_pointer['audit_sha256'],
        'parser_sha256': sha(parser.read_bytes()), 'native_functions_sha256': sha(function_bytes),
        'contracts': contracts, 'source_parameter_shape_matches': source_matches,
        'records': audit, 'boundary_controls': controls,
        'record_count': len(audit), 'advertised_contract_available_records': sum(r['contract_available'] for r in audit),
        'nonempty_actions': sum(r['action'] is not None for r in audit),
        'empty_terminal_records': sum(r['action'] is None for r in audit),
        'bound_search_actions': sum(r.get('native_search_parse', {}).get('bound', False) for r in audit),
        'bound_full_parse_actions': sum(r.get('strict_full_parse', {}).get('bound', False) for r in audit),
        'delivered_signature_count': len(first['signatures']),
        'boundary_check_count': len(controls), 'model_calls': 0, 'gui_actions': 0,
        'history_section_regression_passed': True,
        'official_scores': 0, 'ready_for_online': False,
        'limits': [
            'These are exported action strings, potentially post-wrapper; not original raw model candidates or wire bodies.',
            'Advertised names/parameter shapes are bound for one selected historical run; not all tasks or current environments.',
            'Native strictness at deployment remains unbound; both parser modes are audit-only, neither changes the original controller.',
            'Binding does not enforce annotations, coordinates, element existence, target semantics, execution success or Mirage labels.',
            'Current source signature compatibility does not prove historical source identity.',
        ],
    }
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    (out / 'audit.json').write_bytes(raw)
    for name in ['webmall_delivered_action_contract.py', 'audit_webmall_delivered_contract.py']:
        (out / name).write_bytes((BASE / name).read_bytes())
    seal = {str(p.relative_to(out)): sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    (out / 'sealed-sha256.json').write_text(json.dumps(seal, indent=2), encoding='utf-8')
    pointer = {k: data[k] for k in ['record_count', 'advertised_contract_available_records', 'nonempty_actions',
               'empty_terminal_records', 'bound_search_actions', 'bound_full_parse_actions', 'delivered_signature_count',
               'boundary_check_count', 'ready_for_online', 'model_calls', 'gui_actions']}
    pointer.update(directory=str(out), audit_sha256=sha(raw),
                   seal_sha256=sha((out / 'sealed-sha256.json').read_bytes()))
    (BASE / 'webmall-delivered-contract-current.json').write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
