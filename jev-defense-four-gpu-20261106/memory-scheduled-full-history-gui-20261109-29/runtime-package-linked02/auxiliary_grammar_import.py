"""Private auxiliary grammar graph; canonical main imports remain untouched."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_modules():
    return {key: value for key, value in sys.modules.items()
            if key == 'lmformatenforcer' or key.startswith('lmformatenforcer.')}


def load_auxiliary_grammar():
    package = Path(__file__).resolve().parent
    reference = json.loads((package / 'auxiliary-grammar-identity.json').read_bytes())
    private = package / 'grammar-vendor' / 'lmformatenforcer'
    for name, expected in reference['private_files'].items():
        if _sha(private / name) != expected:
            raise RuntimeError('Private auxiliary grammar source changed: ' + name)
    primary = _canonical_modules()
    if 'lmformatenforcer' not in primary:
        raise RuntimeError('Restore and bind the original main dependency before auxiliary setup')
    expected_primary = Path(reference['canonical_primary_package']).resolve()
    for name, value in primary.items():
        source = getattr(value, '__file__', None)
        if source and not Path(source).resolve().is_relative_to(expected_primary):
            raise RuntimeError('Canonical main grammar came from an unexpected package: ' + name)
    identities = {name: (str(Path(value.__file__).resolve()), _sha(value.__file__))
                  for name, value in primary.items() if getattr(value, '__file__', None)}
    suffix = hashlib.sha256(str(package).encode('utf8')).hexdigest()[:20]
    alias = '_mirage_auxiliary_grammar_' + suffix
    if alias in sys.modules:
        api = sys.modules[alias]
        if Path(api.__file__).resolve() != (private / '__init__.py').resolve():
            raise RuntimeError('Private auxiliary module alias collision')
    else:
        spec = importlib.util.spec_from_file_location(
            alias, private / '__init__.py', submodule_search_locations=[str(private)])
        api = importlib.util.module_from_spec(spec)
        sys.modules[alias] = api
        try:
            spec.loader.exec_module(api)
        except BaseException:
            # Fail closed. A service never proceeds with a partly loaded graph.
            raise
    if _canonical_modules() != primary:
        raise RuntimeError('Auxiliary load modified the canonical main module graph')
    for name, value in primary.items():
        if getattr(value, '__file__', None):
            if identities[name] != (str(Path(value.__file__).resolve()), _sha(value.__file__)):
                raise RuntimeError('Canonical main grammar bytes changed during auxiliary setup')
    private_imports = {}
    for name, value in list(sys.modules.items()):
        if name == alias or name.startswith(alias + '.'):
            path = Path(value.__file__).resolve()
            if not path.is_relative_to(private.resolve()):
                raise RuntimeError('Private auxiliary grammar escaped its source root')
            relative = str(path.relative_to(private.resolve()))
            if relative not in reference['private_files'] or _sha(path) != reference['private_files'][relative]:
                raise RuntimeError('Unpinned private auxiliary module: ' + name)
            private_imports[name] = {'file': str(path), 'sha256': _sha(path)}
    if api.JsonSchemaParser is primary['lmformatenforcer'].JsonSchemaParser:
        raise RuntimeError('Auxiliary is still using the canonical main parser')
    return api, {'alias': alias, 'source_identity_sha256': _sha(package / 'auxiliary-grammar-identity.json'),
                 'private_imports': private_imports, 'canonical_main_module_objects_and_files_unchanged': True}
