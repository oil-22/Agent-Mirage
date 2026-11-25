"""Freeze and verify the post-source-review logical terminal collector."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,sort_keys=True,indent=2)
        stream.write('\n')


def main():
    pointer=HERE/'logical-terminal-collection-preparation-created.json'
    assert not pointer.exists(),'Do not repeat completed preparation'
    root=HERE/('logical-terminal-collection-preparation-'+str(time.time_ns()));root.mkdir()
    package=HERE/'runtime-package'
    manifest_sha=sha(package/'manifest.json')
    assert manifest_sha=='c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    manifest=json.loads((package/'manifest.json').read_bytes())
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    sources={}
    for name in ['logical_terminal_checks.py','check_logical_terminal_checks.py',
                 'collect_logical_terminal_once.py','prepare_logical_terminal_collection_once.py']:
        raw=(HERE/name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest();(root/name).write_bytes(raw)
        compile(raw.decode('utf8'),name,'exec')
    # Compile the actual embedded remote code, without invoking either remote host.
    source=(HERE/'collect_logical_terminal_once.py').read_text(encoding='utf8')
    import ast
    module=ast.parse(source)
    for node in module.body:
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name)and n.id in ['GUI_CODE','SERVICE_CODE']for n in node.targets):
            compile(ast.literal_eval(node.value),'frozen-remote-'+node.targets[0].id,'exec')
    result=subprocess.run([sys.executable,'-B',str(HERE/'check_logical_terminal_checks.py')],
        cwd=HERE,capture_output=True)
    (root/'checks.stdout.txt').write_bytes(result.stdout);(root/'checks.stderr.txt').write_bytes(result.stderr)
    for name,expected in sources.items():assert sha(HERE/name)==expected
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    save(root/'receipt.json',dict(time=time.time(),passed=result.returncode==0,synthetic_CPU_checks=12,
        test_process_exit_code=result.returncode,sources=sources,frozen_manifest_sha256=manifest_sha,
        original_runtime_bytes_unchanged=True,actual_terminal_not_yet_collected_by_this_preparation=True,
        original_remote_files_not_moved_deleted_compressed_or_modified=True,
        source_review_gate_before_current_terminal_outcome_join=True,
        carried_prefix_requires_separate_original_authorities=True,
        new_model_GUI_scorer_paid_calls=0,no_semantic_labels_or_defense_efficacy_established=True))
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    record=dict(root=str(root),passed=result.returncode==0,receipt_sha256=sha(root/'receipt.json'),seal_sha256=sha(root/'seal.json'))
    save(HERE/(('logical-terminal-collection-preparation-created'if result.returncode==0 else
        'logical-terminal-collection-preparation-failed-'+root.name.split('-')[-1])+'.json'),record)
    print(json.dumps(record))
    if result.returncode:
        print(result.stderr.decode('utf8',errors='replace'));raise SystemExit(result.returncode)


if __name__=='__main__':main()
