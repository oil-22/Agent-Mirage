"""Read-only source/visible-trace freeze. Never imports or launches WebMall."""
import ast
import base64
import hashlib
import json
import time
from pathlib import Path

from remote import remote


BASE = Path(__file__).resolve().parent
SOURCES = [
    'run_webmall_mirage.py',
    'qwen_webmall_agent.py',
    'qwen_webmall_visual_price_audit.py',
    'webmall_mirage_injection.py',
    'webmall_stale_screenshot.py',
    'webmall_visible_prefix_replay.py',
    'AgentLab/src/agentlab/agents/generic_agent/generic_agent.py',
    'AgentLab/src/agentlab/agents/dynamic_prompting.py',
    'AgentLab/src/agentlab/llm/chat_api.py',
    'AgentLab/src/agentlab/llm/llm_utils.py',
    'Browsergym/browsergym/core/src/browsergym/core/action/highlevel.py',
    'Browsergym/browsergym/core/src/browsergym/core/action/parsers.py',
]


def main():
    destination = BASE / 'native-adapter-sources' / ('webmall-contract-' + str(time.time_ns()))
    destination.mkdir(parents=True, exist_ok=False)
    code = 'NAMES=' + repr(SOURCES) + '\n' + r'''
import base64,hashlib,json,pathlib
root=pathlib.Path('/data/researcher/src/WebMall'); records=[]
def preserve(p,label):
    before=p.stat();raw=p.read_bytes();after=p.stat()
    assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
    records.append({'source':str(p),'local':label,'sha256':hashlib.sha256(raw).hexdigest(),
        'bytes':len(raw),'stable_stat':True,'body_base64':base64.b64encode(raw).decode()})
for n in NAMES:
    p=root/n;assert p.is_file(),str(p);preserve(p,'source/'+n)
archive=pathlib.Path('/data/researcher/webmall-results/mirage-pure-visual-baseline20-a100-2026-10-06/mirage-image-drop')
run=sorted(p for p in archive.iterdir()if p.is_dir())[0]
preserve(run/'agent_visible_trace.jsonl','archive/agent_visible_trace.jsonl')
preserve(run/'model_delivery.jsonl','archive/model_delivery.jsonl')
# Images are provenance only, never a replacement for live recapture.
subdirs=[p for p in run.iterdir()if p.is_dir()]
assert len(subdirs)==1
for step in range(3):
    p=subdirs[0]/('screenshot_step_'+str(step)+'.png')
    preserve(p,'archive/'+p.name)
print(json.dumps({'run':str(run),'records':records,'read_only':True,'model_calls':0,'gui_actions':0}))
'''
    result = json.loads(remote(code, host='4090', timeout=60))
    records = []
    for record in result['records']:
        body = base64.b64decode(record.pop('body_base64'), validate=True)
        assert hashlib.sha256(body).hexdigest() == record['sha256']
        target = destination / record['local']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        if target.suffix == '.py':
            tree = ast.parse(body)
            record['definitions'] = [
                {'name': node.name, 'line': node.lineno, 'end_line': node.end_lineno}
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            ]
        records.append(record)
    manifest = {
        'directory': str(destination), 'archive_run': result['run'], 'files': records,
        'source_files': len(SOURCES), 'archive_files': len(records) - len(SOURCES),
        'read_only_remote': True, 'native_sources_imported': False,
        'model_calls': 0, 'gui_actions': 0, 'official_evaluations': 0,
        'ready_for_online': False,
        'scope': 'Current source plus legal exported archive, not historical source revision or actual wire-body identity. No evaluator answers read.',
    }
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    (destination / 'source-manifest.json').write_bytes(raw)
    pointer = {
        'directory': str(destination), 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
        'source_files': len(SOURCES), 'archive_files': len(records) - len(SOURCES),
        'ready_for_online': False, 'model_calls': 0, 'gui_actions': 0,
    }
    (BASE / 'webmall-native-contract-source-current.json').write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
