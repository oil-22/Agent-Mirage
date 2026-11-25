"""Extract the frozen original parse function; do not import its browser module."""
import ast
import json
import re
from control import HERE, sha


def parse_original():
    source = HERE / 'package/native-parser-source.py'
    manifest = json.loads((HERE / 'package/manifest.json').read_bytes())
    assert sha(source) == manifest['files']['native-parser-source.py']
    tree = ast.parse(source.read_text(encoding='utf8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse']
    assert len(functions) == 1
    namespace = {'json': json, 're': re}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source) + ':parse', 'exec'), namespace)
    return namespace['parse']
