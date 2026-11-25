"""Export original new31 candidates/full lawful inputs before current outcomes."""
import argparse
import importlib.util
from pathlib import Path
import sys

from orchestrate import HERE, OUTPUT, GUIROOT


def main(max_new):
    old = HERE.parent / 'full-history-gui-development-20261109-23'
    sys.path.insert(0, str(old))
    spec = importlib.util.spec_from_file_location('unchanged_source_first_collector23', old / 'collect_source_first_packets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE, module.ROOT3090, module.ROOT4090 = HERE, OUTPUT, GUIROOT
    before = 'assert h(ast.dump(node,include_attributes=False).encode())==PARSER_AST_SHA'
    assert module.GUI_SOURCE.count(before) == 1
    module.GUI_SOURCE = module.GUI_SOURCE.replace(before,
        "assert h(source)=='af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'")
    module.GUI_SOURCE = module.GUI_SOURCE.replace("'native_parser_AST_sha256':PARSER_AST_SHA",
        "'native_parser_AST_sha256':h(ast.dump(node,include_attributes=False).encode())")
    module.main(max_new)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-new', type=int, default=10)
    args = parser.parse_args()
    assert 1 <= args.max_new <= 70
    main(args.max_new)
