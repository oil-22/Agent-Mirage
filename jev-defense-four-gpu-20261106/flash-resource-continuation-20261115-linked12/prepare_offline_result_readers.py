"""Bind the existing read-only offline10 audit/export to its continuation root."""
import ast
import json
import time
from pathlib import Path
from control import HERE, save, sha
from offline_followup_control import PREP, REMOTE, OUTPUT


def main():
    old = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
    rows = {}
    for name in ['audit_offline_development_postexit.py', 'export_offline_source_packets.py']:
        data = (old / name).read_bytes()
        text = data.decode('utf8')
        changes = {}
        if name.startswith('audit_'):
            changes = {
                "PREP = HERE / 'evidence-discipline-offline-preparation-01'": "PREP = HERE / " + repr(PREP.name),
                "PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-development-20261114-01'": 'PACKAGE = ' + repr(REMOTE),
                "OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-development-20261114-01'": 'OUTPUT = ' + repr(OUTPUT)}
            for before, after in changes.items():
                assert text.count(before) == 1
                text = text.replace(before, after)
        ast.parse(text)
        with (HERE / name).open('xb') as f:
            f.write(text.encode('utf8') if changes else data)
        rows[name] = {'original_path': str(old / name), 'original_sha256': sha(old / name),
                      'reader_sha256': sha(HERE / name), 'metadata_path_replacements_only': changes}
    dest = HERE / ('offline-result-reader-preparation-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'preparation.json', {'time': time.time(), 'files': rows,
         'prepared_package_manifest_sha256': sha(PREP / 'package/offline-manifest.json'),
         'actual_postexit_audit_or_export_executed': False,
         'new_model_GUI_calls': 0, 'runtime_sources_changed': False})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'preparation': str(dest), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
