"""Join GUI32 execution only after immutable source labels have been sealed."""
import argparse
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, action='append', required=True)
    spec = importlib.util.spec_from_file_location(
        'source_sealed_join23_read_only', OLD / 'join_sealed_source_reviews.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.ROOT4090 = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    module.main(parser.parse_args().review)
