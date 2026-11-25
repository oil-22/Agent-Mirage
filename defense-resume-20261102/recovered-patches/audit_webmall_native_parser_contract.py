"""CPU audit of frozen native grammar and exported actions; no browser imports."""
import ast
import base64
import hashlib
import json
import time
import types
from pathlib import Path

from remote import remote

BASE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def node_source(text, name, parent=None):
    tree = ast.parse(text)
    if parent:
        tree = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == parent)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return node


def main():
    pointer = json.loads((BASE / 'webmall-native-contract-source-current.json').read_bytes())
    source_root = Path(pointer['directory'])
    raw = (source_root / 'source-manifest.json').read_bytes()
    assert sha(raw) == pointer['manifest_sha256']
    manifest = json.loads(raw)
    for row in manifest['files']:
        assert sha((source_root / row['local']).read_bytes()) == row['sha256']
    out = BASE / 'native-adapter-sources' / ('webmall-parser-audit-' + str(time.time_ns()))
    out.mkdir(exist_ok=False)
    extra = json.loads(remote(r'''
import pathlib,json,base64,hashlib
root=pathlib.Path('/data/researcher/src/WebMall');rows=[]
for n in ['AgentLab/src/agentlab/agents/generic_agent/generic_agent_prompt.py','Browsergym/browsergym/core/src/browsergym/core/action/functions.py']:
    p=root/n;s=p.stat();raw=p.read_bytes();e=p.stat()
    assert (s.st_size,s.st_mtime_ns,s.st_ino)==(e.st_size,e.st_mtime_ns,e.st_ino)
    rows.append({'path':str(p),'local':n,'sha256':hashlib.sha256(raw).hexdigest(),'body':base64.b64encode(raw).decode()})
print(json.dumps(rows))
''', host='4090', timeout=40))
    for row in extra:
        raw = base64.b64decode(row.pop('body'), validate=True)
        assert sha(raw) == row['sha256']
        p = out / 'source' / row['local']
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        ast.parse(raw)
    browser = source_root / 'source/Browsergym/browsergym/core/src/browsergym/core/action'
    parser_text = (browser / 'parsers.py').read_text(encoding='utf-8')
    # This exact frozen module only defines literal parsers and dataclasses.
    # It does not import BrowserGym, create a browser or execute a GUI call.
    parsed = ast.parse(parser_text)
    imported = {n.name for n in ast.walk(parsed) if isinstance(n, ast.alias)}
    assert imported == {'ast', 'pyparsing', 'dataclass', 'Any'}, imported
    parser_module = types.ModuleType('_frozen_webmall_literal_parser')
    import sys
    sys.modules[parser_module.__name__] = parser_module
    exec(compile(parsed, str(browser / 'parsers.py'), 'exec'), parser_module.__dict__)
    native_parser = parser_module.highlevel_action_parser
    highlevel = (browser / 'highlevel.py').read_text(encoding='utf-8')
    method = node_source(highlevel, 'to_python_code', 'HighLevelActionSet')
    method_code = ast.Module(body=[method], type_ignores=[])
    namespace = {'highlevel_action_parser': native_parser}
    exec(compile(method_code, str(browser / 'highlevel.py'), 'exec'), namespace)
    # Only the returned string is inspected. It is never executed.
    action_subsets = next(n.value for n in ast.parse(highlevel).body
                          if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ACTION_SUBSETS' for t in n.targets))
    names = sorted({n.id for n in ast.walk(action_subsets) if isinstance(n, ast.Name)} | {'noop'})
    proxy = types.SimpleNamespace(strict=False, multiaction=False, python_includes='',
                                  action_set={name: None for name in names})
    convert = lambda text: namespace['to_python_code'](proxy, text)
    rows = [json.loads(line) for line in (source_root / 'archive/agent_visible_trace.jsonl').read_text(encoding='utf-8').splitlines()]
    actions = []
    for row in rows:
        raw_action = row['action']
        item = {'step': row['step'], 'raw_action': raw_action,
                'raw_action_sha256': sha(json.dumps(raw_action, ensure_ascii=False).encode())}
        try:
            item['native_conversion_string'] = convert(raw_action)
            item['converted'] = True
        except Exception as exc:
            item['converted'] = False
            item['error'] = type(exc).__name__ + ': ' + str(exc)
        actions.append(item)
    controls = []
    examples = [
        ('native_noop', 'noop()', True),
        ('native_noop_duration', 'noop(500)', True),
        ('native_bid', "click('42')", True),
        ('native_named_arg', "fill(bid='42', value='text')", True),
        ('native_scroll', 'scroll(0, -500)', True),
        ('literal_url', "goto('http://localhost:8081')", True),
        ('two_actions', "click('42')\nclick('43')", False),
        ('empty', '', False),
        ('unknown_action', 'unlisted_action()', False),
        ('bare_wait', 'WAIT', False),
        # Native strict=False searches for function calls and ignores surrounding prose.
        ('native_surrounding_prose', "I will click next: click('42') trailing text", True),
        ('nested_nonliteral', "click(resolve_target())", False),
    ]
    for name, text, expected in examples:
        try:
            code = convert(text)
            observed, error = True, None
        except Exception as exc:
            code, observed, error = None, False, type(exc).__name__ + ': ' + str(exc)
        controls.append({'name': name, 'input': text, 'converted': observed,
                         'expected_native_behavior': expected, 'matches': observed == expected,
                         'returned_code_not_executed': code, 'error': error})
    assert all(c['matches'] for c in controls), controls
    findings = {
        'directory': str(out), 'source_root': str(source_root),
        'parent_manifest_sha256': pointer['manifest_sha256'], 'supplemental_sources': extra,
        'native_parser_file_sha256': sha(parser_text.encode()),
        'native_conversion_ast_sha256': sha(ast.dump(method, include_attributes=False).encode()),
        'controls': controls, 'archive_actions': actions,
        'archive_action_count': len(actions), 'converted_archive_actions': sum(a['converted'] for a in actions),
        'configuration': {'strict': False, 'multiaction': False, 'action_names': names},
        'configuration_scope': 'Current-source single-action setting with UNION of declared subset names; archived deployed subset/strict flags unbound, so not a full allowed-action audit.',
        'source_findings': [
            'MainPrompt and fit_tokens build a dynamic two-message request; complete wire-body identity is not supplied by a trace with images replaced by hashes.',
            'Current price-audit source sets 12000 input/prompt tokens, 2048 output and max_trunc_itr80. It can shrink historical material; do not silently reuse as full-history defense.',
            'Current wrapper includes first-action selection, empty-response nonthinking fallback, repair calls and repeated-action rewriting. Exact historical effective branches remain unbound.',
            'Pure-visual runner overwrites task-specific extra_instructions; do not assume every task-specific guidance branch reaches that profile.',
            'Native bare WAIT is not an action; native noop() is the declared no-op. No semantic Mirage labels assigned.',
        ],
        'native_gui_modules_imported': False, 'generated_code_executed': False,
        'model_calls': 0, 'gui_actions': 0, 'official_evaluations': 0, 'ready_for_online': False,
        'remaining': ['Exact archived/runtime wire requests and generation defaults/thinking branches',
                      'Actual benchmark action subsets and strictness; complete native signature checks',
                      'Original screenshots and same-live recapture/mask ownership',
                      'Isolated task ownership/locks and official scorer transport',
                      'Full-history preservation and budget/retry conditions before formal experiments'],
    }
    raw = (json.dumps(findings, ensure_ascii=False, indent=2) + '\n').encode()
    (out / 'contract-audit.json').write_bytes(raw)
    result = {'directory': str(out), 'audit_sha256': sha(raw),
              'source_parent_sha256': pointer['manifest_sha256'],
              'boundary_checks': len(controls), 'archive_actions': len(actions),
              'converted_archive_actions': findings['converted_archive_actions'],
              'ready_for_online': False, 'model_calls': 0, 'gui_actions': 0}
    (BASE / 'webmall-native-contract-current.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
