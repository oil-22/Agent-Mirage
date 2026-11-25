"""Preserve original single-trajectory controller checks without importing finalizers."""
import ast
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    old = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
    original = old / 'finalize_GUI_controller_bindings.py'
    source = original.read_text('utf8')
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_controller')
    binding = next(n for n in tree.body if isinstance(n, ast.Assign) and
                   any(isinstance(t, ast.Name) and t.id == 'GUI_READER' for t in n.targets))
    reader = ast.literal_eval(binding.value)
    text = ('"""Original controller reader/checks only; no all29 finalizer import."""\n'
            'import hashlib\nfrom native_parser_reader import parse_original\n\n'
            'GUI_READER = ' + repr(reader) + '\n\n' + ast.get_source_segment(source, function) + '\n')
    ast.parse(text)
    copied = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef))
    assert ast.dump(copied) == ast.dump(function)
    target = HERE / 'controller_audit_reader.py'
    if target.exists():
        assert target.read_text('utf8') == text
    else:
        with target.open('x', encoding='utf8', newline='\n') as f:
            f.write(text)
    files = {}
    for name in ['join_completed_source_review.py', 'inspect_terminals.py']:
        data = (old / name).read_bytes()
        if name.startswith('join_'):
            before = 'from finalize_GUI_controller_bindings import GUI_READER, check_controller, parse_original'
            s = data.decode('utf8')
            assert s.count(before) == 1
            data = s.replace(before, 'from controller_audit_reader import GUI_READER, check_controller, parse_original').encode('utf8')
        ast.parse(data.decode('utf8'))
        target = HERE / name
        if target.exists():
            assert target.read_bytes() == data, name
        else:
            with target.open('xb') as f:
                f.write(data)
        files[name] = {'original': str(old / name), 'original_sha256': sha(old / name),
                       'reader_sha256': sha(HERE / name), 'only_import_changed': name.startswith('join_')}
    dest = HERE / ('controller-reader-preparation-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'preparation.json', {'time': time.time(), 'original_finalizer_source_sha256': sha(original),
         'controller_check_function_AST_and_GUI_reader_exactly_preserved': True,
         'controller_reader_sha256': sha(HERE / 'controller_audit_reader.py'), 'files': files,
         'runtime_sources_changed': False, 'new_model_GUI_calls': 0,
         'actual_complete_trajectory_or_postexit_finalization_not_executed': True})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'preparation': str(dest), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
