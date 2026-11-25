"""Incremental source-first review packets for NEW29 actual candidates only."""
import argparse
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))


def main(max_new):
    spec = importlib.util.spec_from_file_location('source_first_collector23_read_only_source', OLD / 'collect_source_first_packets.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.HERE = HERE
    module.ROOT3090 = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    module.ROOT4090 = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    before = 'assert h(ast.dump(node,include_attributes=False).encode())==PARSER_AST_SHA'
    assert module.GUI_SOURCE.count(before) == 1
    module.GUI_SOURCE = module.GUI_SOURCE.replace(before,
        "assert h(source)=='af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'")
    module.GUI_SOURCE = module.GUI_SOURCE.replace("'native_parser_AST_sha256':PARSER_AST_SHA",
        "'native_parser_AST_sha256':h(ast.dump(node,include_attributes=False).encode())")
    # carryover_replay_candidate is intentionally excluded by the original
    # exact kind comparison: original candidate11 was already fully reviewed.
    module.main(max_new)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--max-new', type=int, default=20)
    value = parser.parse_args().max_new
    assert 1 <= value <= 70
    main(value)
