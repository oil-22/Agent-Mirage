"""Copy read-only evidence readers, without importing a live model or finalizer."""
import ast
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    old = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
    files = {}
    for name in ['audit_flash_incremental.py', 'bind_source_prefix_review.py']:
        data = (old / name).read_bytes()
        if name == 'bind_source_prefix_review.py':
            text = data.decode('utf8')
            before = 'from finalize_GUI_controller_bindings import parse_original'
            assert text.count(before) == 1
            data = text.replace(before, 'from native_parser_reader import parse_original').encode('utf8')
        ast.parse(data.decode('utf8'))
        with (HERE / name).open('xb') as f:
            f.write(data)
        files[name] = {'original': str(old / name), 'original_sha256': sha(old / name),
                       'reader_sha256': sha(HERE / name),
                       'only_parser_import_changed': name == 'bind_source_prefix_review.py'}
    tree = ast.parse((HERE / 'native_parser_reader.py').read_text('utf8'))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) and
                   any(a.name in ['torch', 'transformers', 'browser_env'] for a in n.names)
                   for n in ast.walk(tree))
    dest = HERE / ('local-audit-reader-preparation-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'preparation.json', {'time': time.time(), 'files': files,
         'parser_reader_sha256': sha(HERE / 'native_parser_reader.py'),
         'original_parse_AST_only_no_module_import': True,
         'original_runtime_package_changed': False, 'new_model_GUI_calls': 0})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'preparation': str(dest), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
