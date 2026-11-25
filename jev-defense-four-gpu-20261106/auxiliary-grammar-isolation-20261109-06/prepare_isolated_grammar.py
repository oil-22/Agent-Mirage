"""Freeze a linked source repair. No live package or failed output is edited."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-gui-bounded-evidence-20261109-03' / 'runtime-package'
NEW = HERE / 'isolated-runtime-source'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


NEW.mkdir(exist_ok=False)
for name in ['bounded_schema.py', 'native_format_bridge.py', 'bounded_auxiliary.py']:
    shutil.copy2(OLD / name, NEW / name)
shutil.copytree(OLD / 'grammar-vendor', NEW / 'grammar-vendor',
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
shutil.copy2(HERE / 'auxiliary_grammar_import.py', NEW / 'auxiliary_grammar_import.py')
schema = (NEW / 'bounded_schema.py').read_text(encoding='utf8')
schema = schema.replace('from lmformatenforcer import JsonSchemaParser, CharacterLevelParserConfig',
    'from auxiliary_grammar_import import load_auxiliary_grammar\n    api,_=load_auxiliary_grammar()\n    JsonSchemaParser,CharacterLevelParserConfig=api.JsonSchemaParser,api.CharacterLevelParserConfig')
schema = schema.replace('from lmformatenforcer import JsonSchemaParser,CharacterLevelParserConfig',
    'from auxiliary_grammar_import import load_auxiliary_grammar\n    api,_=load_auxiliary_grammar()\n    JsonSchemaParser,CharacterLevelParserConfig=api.JsonSchemaParser,api.CharacterLevelParserConfig')
assert 'from lmformatenforcer' not in schema
(NEW / 'bounded_schema.py').write_text(schema, encoding='utf8')
bridge = (NEW / 'native_format_bridge.py').read_text(encoding='utf8')
bridge = bridge.replace('from lmformatenforcer import TokenEnforcerTokenizerData',
    'from auxiliary_grammar_import import load_auxiliary_grammar\n    api,_=load_auxiliary_grammar()\n    TokenEnforcerTokenizerData=api.TokenEnforcerTokenizerData')
bridge = bridge.replace('from lmformatenforcer import TokenEnforcer',
    'from auxiliary_grammar_import import load_auxiliary_grammar\n        api,_=load_auxiliary_grammar()\n        TokenEnforcer=api.TokenEnforcer')
assert 'from lmformatenforcer' not in bridge
(NEW / 'native_format_bridge.py').write_text(bridge, encoding='utf8')
aux = (NEW / 'bounded_auxiliary.py').read_text(encoding='utf8')
aux = aux.replace('    data=build_token_data(processor.tokenizer)',
    "    from auxiliary_grammar_import import load_auxiliary_grammar\n    api,import_proof=load_auxiliary_grammar()\n    save(root/'auxiliary-grammar-actual-imports.json',import_proof)\n    data=build_token_data(processor.tokenizer)")
(NEW / 'bounded_auxiliary.py').write_text(aux, encoding='utf8')
diagnostic = HERE / 'diagnostic-collection' / '1794205640887040400' / 'original' / 'receipt.json'
v = json.loads(diagnostic.read_bytes())
assert v['actual_production_uses_unpatched_primary_grammar']
primary_package = str(Path(v['production_imports']['lmformatenforcer']['file']).parent).replace('\\', '/')
private = NEW / 'grammar-vendor' / 'lmformatenforcer'
files = {p.relative_to(private).as_posix(): sha(p) for p in private.rglob('*') if p.is_file()}
save(NEW / 'auxiliary-grammar-identity.json', {'canonical_primary_package': primary_package,
    'private_files': files, 'source_diagnostic_receipt_sha256': sha(diagnostic),
    'original_main_graph_and_validator_unchanged': True})
save(HERE / 'source-repair-preparation.json', {'time': time.time(),
    'parent_manifest_sha256': '584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67',
    'source_diagnostic_receipt': str(diagnostic), 'diagnostic_sha256': sha(diagnostic),
    'new_source': str(NEW), 'new_CPU_integration_replay_pending': True,
    'new_model_GUI_calls': 0, 'live_condition_modified': False,
    'change': 'Use a pinned private auxiliary module namespace after actual canonical primary dependency restore; preserve both independent import graphs.',
    'limits': ['Does not fix image-reading accuracy, point localization or normal-operation false blocks.',
               'Byte grammar still permits up to four bytes per declared character; exact original final length validator can still withhold long strings.',
               'No old input is regenerated and no terminal or old queue is resumed.']})
save(NEW / 'source-seal.json', {p.relative_to(NEW).as_posix(): sha(p) for p in NEW.rglob('*') if p.is_file()})
print(json.dumps({'new_source': str(NEW), 'seal_sha256': sha(NEW / 'source-seal.json'),
                  'canonical_primary_package': primary_package, 'model_GUI_calls': 0}))
