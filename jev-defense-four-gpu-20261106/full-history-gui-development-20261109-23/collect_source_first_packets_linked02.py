"""Linked metadata repair: bind identical native bytes across Python AST versions.

The initial failed collector and remote operation remain sealed. No experimental
source, parser, model input, original result, or running process is modified.
"""
import argparse
import json
from pathlib import Path

import collect_source_first_packets as original
from remote_control import HERE, sha


def main(max_new):
    failed_sha = 'ef1cbbe6485d6f50228b07b50b403a9ad3bec7ba0d47392a54938c91e0781649'
    assert sha(Path(original.__file__)) == failed_sha
    preservation = HERE / 'source-first-collector-failure-preservation-1794222574742163300'
    assert sha(preservation / 'seal.json') == '38c6f570401257e10d3cb97cdfe058f7a10c82b0f7997a07d1186b4b92671666'
    for name, expected in json.loads((preservation / 'seal.json').read_bytes()).items():
        assert sha(preservation / name) == expected
    native_sha = sha(HERE.parent / 'complete-history-main-preflight-20261109-22/runtime-package/native-parser-source.py')
    assert native_sha == 'af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'
    old_check = 'assert h(ast.dump(node,include_attributes=False).encode())==PARSER_AST_SHA'
    assert original.GUI_SOURCE.count(old_check) == 1
    original.GUI_SOURCE = original.GUI_SOURCE.replace(old_check, 'assert h(source)==' + repr(native_sha))
    original.GUI_SOURCE = original.GUI_SOURCE.replace(
        "'native_parser_AST_sha256':PARSER_AST_SHA",
        "'native_parser_AST_sha256':h(ast.dump(node,include_attributes=False).encode())")
    original.main(max_new)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-new', type=int, default=20)
    args = parser.parse_args()
    assert 1 <= args.max_new <= 70
    main(args.max_new)
