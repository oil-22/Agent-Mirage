"""Copy only named source modules; never import or launch archived runners."""
import ast
import base64
import hashlib
import json
import time
from pathlib import Path

from remote import remote

BASE = Path(__file__).resolve().parent
SOURCES = {
    'webmall/qwen_webmall_agent.py': '/data/researcher/src/WebMall/qwen_webmall_agent.py',
    'webmall/run_webmall_study_qwen_visual.py': '/data/researcher/src/WebMall/run_webmall_study_qwen_visual.py',
    'webmall/webmall_mirage_injection.py': '/data/researcher/src/WebMall/webmall_mirage_injection.py',
    'webmall/webmall_stale_screenshot.py': '/data/researcher/src/WebMall/webmall_stale_screenshot.py',
    'androidworld/android_native.py': '/data/researcher/androidworld-uitars7-2026-10-15/deployment/android_native.py',
    'androidworld/run_android_pilot.py': '/data/researcher/androidworld-uitars7-2026-10-15/deployment/run_android_pilot.py',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    out = BASE / 'native-adapter-sources' / ('remaining-freeze-' + str(time.time_ns()))
    out.mkdir(parents=True, exist_ok=False)
    code = 'SOURCES=' + repr(SOURCES) + '\n' + '''
import pathlib,json,hashlib,base64
rows={}
for name,source in SOURCES.items():
 raw=pathlib.Path(source).read_bytes()
 rows[name]={'source':source,'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
print(json.dumps(rows))
'''
    rows = json.loads(remote(code, host='4090', timeout=60))
    inventory = json.loads((BASE / 'native-adapter-sources/discovery-20261027.json').read_bytes())
    expected = {r['directory'] + '/' + f['name']: f['sha256'] for r in inventory['rows'] for f in r.get('python_sources', [])}
    for name, row in rows.items():
        raw = base64.b64decode(row.pop('base64'))
        assert digest(raw) == row['sha256'] == expected[row['source']]
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        tree = ast.parse(raw)
        row['top_level_definitions'] = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        row['syntax_parsed_only'] = True
    record = {
        'scope': 'Source-only adapter preparation for the remaining authorized configurations; no online readiness claim',
        'source_files': rows, 'model_calls': 0, 'gui_actions': 0, 'official_evaluations': 0,
        'ready_for_online': False, 'remote_changes': False,
        'android_note': 'These sources define the native UI-TARS Android dialect. They are not evidence of an original27B Android request or a source-bound27B defense actor; that binding is still required.',
        'webmall_note': 'The remote original Qwen WebMall agent is preserved. Full dynamically assembled prompt, effective generation defaults, parser, same-live recapture and evaluator binding remain to be verified against actual legal requests.',
        'remaining': ['Original source-bound full legal request and parser contracts for each dataset',
                      'Original image grids/coordinates/button masks without external resizing or truncation',
                      'Strict controller integration preserving each native action dialect and full history',
                      'Verified isolated environment ownership/locks and same-live recapture',
                      'Official scorer transport isolated from online checker input',
                      'Real source-bound positive, negative and WAIT controls before separate live preflights'],
    }
    raw = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    (out / 'provenance.json').write_bytes(raw)
    ptr = {'directory': str(out), 'provenance_sha256': digest(raw), 'ready_for_online': False,
           'source_files': len(rows), 'model_calls': 0, 'gui_actions': 0}
    (BASE / 'remaining-native-source-freeze-current.json').write_text(json.dumps(ptr, indent=2), encoding='utf-8')
    print(json.dumps(ptr))


if __name__ == '__main__':
    main()
