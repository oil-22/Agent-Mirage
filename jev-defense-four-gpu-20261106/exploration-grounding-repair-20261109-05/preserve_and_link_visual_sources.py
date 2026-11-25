"""Preserve the local parse failure and prepare a distinct linked renderer."""
from pathlib import Path
import hashlib
import json
import time
import traceback

HERE = Path(__file__).resolve().parent
old = HERE / 'prepare_visual_sources.py'
preservation = HERE / ('renderer-parse-failure-' + str(time.time_ns()))
preservation.mkdir()
raw = old.read_bytes()
(preservation / old.name).write_bytes(raw)
try:
    compile(raw.decode('utf8'), str(old), 'exec')
except SyntaxError:
    failure = traceback.format_exc()
else:
    raise AssertionError('Expected original parse failure is not reproducible')
(preservation / 'failure.txt').write_text(failure, encoding='utf8')
source = raw.decode('utf8')
assert source.count("CODE=r'''\n") == 1
assert source.count("\n'''\nout,op=remote") == 1
source = source.replace("CODE=r'''\n", 'CODE=r"""\n').replace(
    "\n'''\nout,op=remote", '\n"""\nout,op=remote')
new = HERE / 'prepare_visual_sources_linked02.py'
compile(source, str(new), 'exec')
with new.open('x', encoding='utf8', newline='\n') as stream:
    stream.write(source)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = {
    'time': time.time(), 'failure_stage': 'local Python parsing before remote call',
    'preserved_source_sha256': digest(preservation / old.name),
    'failure_sha256': digest(preservation / 'failure.txt'),
    'linked_source': str(new), 'linked_source_sha256': digest(new),
    'change': 'Disambiguate outer Python literal delimiters only.',
    'original_source_modified': False, 'new_model_GUI_or_remote_calls': 0,
    'offline_renderer_not_yet_run': True,
}
with (preservation / 'receipt.json').open('x', encoding='utf8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
with (preservation / 'seal.json').open('x', encoding='utf8') as stream:
    json.dump({p.name: digest(p) for p in preservation.iterdir() if p.is_file()},
              stream, indent=2)
    stream.write('\n')
print(json.dumps({'preserved': str(preservation), 'linked_source': str(new),
                  'parse_repair_checked': True, 'model_GUI_calls': 0}))
