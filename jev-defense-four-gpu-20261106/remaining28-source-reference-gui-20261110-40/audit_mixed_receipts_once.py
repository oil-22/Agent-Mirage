"""Apply the existing strict auditor to original new31 native/GUI receipts."""
import argparse
import importlib.util
from pathlib import Path
import sys

import orchestrate as current


def main(evidence, requested):
    old = current.HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32'
    sys.path.insert(0, str(old))
    spec = importlib.util.spec_from_file_location('strict_composed_mixed_auditor32', old / 'audit_mixed_receipts_once.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ['HERE', 'PACKAGE', 'OUTPUT', 'GUIROOT', 'REMOTE_PACKAGE', 'COMMON', 'remote', 'save', 'sha']:
        setattr(module, name, getattr(current, name))
    module.main(evidence, requested)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--request', action='append', required=True)
    args = parser.parse_args()
    main(args.evidence.resolve(), args.request)
