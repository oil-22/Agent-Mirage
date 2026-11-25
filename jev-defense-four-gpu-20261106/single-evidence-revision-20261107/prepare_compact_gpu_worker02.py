"""Create a linked worker; never import model libraries, read weights or use SSH."""
import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE / 'native_image_gpu_preflight.py'
target = HERE / 'native_image_gpu_preflight_compact02.py'
text = source.read_text(encoding='utf-8')
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'a451142e4233913cc1fca4c86421b9feeb3655c5ad3eed6643e010b35db9fbfb'
text = text.replace("OUTPUT_CAP=2048", "OUTPUT_CAP=2048\nWEIGHT_REUSE_SOURCE_ROOT='/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01'")
text = text.replace("'metadata_files','weight_files','requests','generation','limits'}", "'metadata_files','weight_files','requests','generation','limits','current_weight_identity_reuse'}")
text = text.replace("!=['S01','S07','S13','S25']", "!=['S04','S10','S16','S19']")
start = text.index('def current_weight_identity(')
end = text.index('\ndef run(', start)
replacement = '''def current_weight_identity(m,root,journal):
    # Reuse only a completed, sealed full-hash proof. The current model load
    # still has before-load and unchanged run() after-load stat gates.
    reuse=m['current_weight_identity_reuse'];source=Path(WEIGHT_REUSE_SOURCE_ROOT)
    fields={'identity_path','identity_sha256','worker_seal_path','worker_seal_sha256',
        'terminal_manifest_path','terminal_manifest_sha256'}
    if not isinstance(reuse,dict)or set(reuse)!=fields:
        raise ValueError('Exact six-field current weight reuse binding required')
    expected_paths={'identity_path':source/'worker/current-weight-identity.json',
        'worker_seal_path':source/'worker/seal.json','terminal_manifest_path':source/'terminal-manifest.json'}
    if any(Path(reuse[key])!=path for key,path in expected_paths.items()):
        raise ValueError('Only the first completed terminal full-hash source may be reused')
    def checked_json(path,expected):
        path=Path(path);before=path.stat();raw=path.read_bytes();after=path.stat()
        if (digest(raw)!=expected or (before.st_size,before.st_mtime_ns,before.st_ino)!=
            (after.st_size,after.st_mtime_ns,after.st_ino)):
            raise ValueError('Immutable proof changed or was unstable: '+str(path))
        return json.loads(raw)
    manifest=checked_json(reuse['terminal_manifest_path'],reuse['terminal_manifest_sha256'])
    seal=checked_json(reuse['worker_seal_path'],reuse['worker_seal_sha256'])
    proof=checked_json(reuse['identity_path'],reuse['identity_sha256'])
    if (manifest.get('worker/seal.json')!=reuse['worker_seal_sha256']or
        manifest.get('worker/current-weight-identity.json')!=reuse['identity_sha256']):
        raise ValueError('Outer terminal manifest does not bind the exact full-hash proof and seal')
    entries=seal.get('files',[])
    if not isinstance(entries,list)or len({x['path']for x in entries})!=len(entries):
        raise ValueError('Original worker seal has missing or duplicate entries')
    sealed={x['path']:x['sha256']for x in entries}
    if (sealed.get('current-weight-identity.json')!=reuse['identity_sha256']or
        sealed.get('terminal.json')!=manifest.get('worker/terminal.json')or
        not sealed.get('terminal.json')or not manifest.get('exit.json')):
        raise ValueError('Original worker seal does not bind identity and terminal')
    terminal=checked_json(source/'worker/terminal.json',sealed['terminal.json'])
    exited=checked_json(source/'exit.json',manifest['exit.json'])
    if (terminal.get('status')!='completed_four_first_attempts'or terminal.get('error')is not None or
        terminal.get('attempted_request_ids')!=['S01','S07','S13','S25']or
        any(terminal.get(k)!=v for k,v in {'attempted_requests':4,'completed_requests':4,
            'failed_incomplete_requests':0,'unattempted':0}.items())or
        exited.get('worker_exit_code')!=0 or exited.get('launcher_exit_code')!=0):
        raise ValueError('Only a fully completed, normally exited original proof can be reused')
    prior=m['prior_weight_identity'];old=checked_json(prior['path'],prior['sha256'])['files']
    official=m['official_base_api'];api=checked_json(official['path'],official['sha256'])
    if api.get('id')!=BASE_REPO or api.get('sha')!=BASE_REVISION:
        raise ValueError('Official API identity differs from the frozen base revision')
    if (proof.get('official_LFS_current_shard_identity_verified')is not True or
        proof.get('official_pinned_base_api_sha256')!=official['sha256']):
        raise ValueError('Original full-hash proof lacks the same official pinned LFS identity')
    native={item['rfilename']:item for item in api['siblings']if item['rfilename'].endswith('.safetensors')}
    rows=m['weight_files'];previous=proof.get('complete_current_shards',[])
    if (len(rows)!=4 or len({r['filename']for r in rows})!=4 or len(previous)!=4 or
        len({r['filename']for r in previous})!=4):
        raise ValueError('Exactly four unique complete shard identities are required')
    previous={row['filename']:row for row in previous}
    model=Path(MODEL_PATH);metadata=[];metadata_raw={}
    if len(m['metadata_files'])!=9 or len({r['filename']for r in m['metadata_files']})!=9:
        raise ValueError('All nine unique native metadata files are required')
    if proof.get('metadata')!=m['metadata_files']:
        raise ValueError('Current native metadata differs from the sealed original full-hash proof')
    for row in m['metadata_files']:
        path=model/row['filename'];before=path.stat();raw=path.read_bytes();after=path.stat()
        if (row['bytes']!=len(raw)or row['sha256']!=digest(raw)or
            (before.st_size,before.st_mtime_ns,before.st_ino)!=
            (after.st_size,after.st_mtime_ns,after.st_ino)):
            raise ValueError('Current native metadata mismatch: '+row['filename'])
        write_raw(root/('metadata--'+row['filename']),raw);metadata.append(row)
        metadata_raw[row['filename']]=raw
    index=json.loads(metadata_raw['model.safetensors.index.json'])
    inventory=set(index['weight_map'].values())
    if inventory!={r['filename']for r in rows}or set(native)!=inventory or set(previous)!=inventory:
        raise ValueError('CPU, official, current index and sealed proof shard inventories differ')
    allowed_files={r['filename']for r in metadata}|inventory|{'README.md'}
    if {p.name for p in model.iterdir()if p.is_file()}!=allowed_files:
        raise ValueError('Native model file set changed, including extra generation/adapter defaults')
    verified=[]
    for row in rows:
        stop_boundary(root)
        name=row['filename'];record=old['Qwen3.5-9B/'+name];known=previous[name]
        if (any(record.get(k)!=row[k]for k in ['bytes','sha256'])or
            any(known.get(k)!=row[k]for k in ['bytes','sha256'])or
            known.get('current_sha256')!=row['sha256']or
            native[name]['lfs']['sha256']!=row['sha256']or native[name]['lfs']['size']!=row['bytes']):
            raise ValueError('Reused SHA identity differs from original, historical or official proof')
        path=model/name;before=path.stat();after=path.stat()
        expected=(row['bytes'],known['mtime_ns'],known['inode'])
        if ((before.st_size,before.st_mtime_ns,before.st_ino)!=expected or
            (after.st_size,after.st_mtime_ns,after.st_ino)!=expected):
            raise ValueError('Current shard stat continuity failed: '+name)
        result=dict(row,reused_full_sha256=row['sha256'],mtime_ns=after.st_mtime_ns,inode=after.st_ino)
        verified.append(result);journal.append('current_shard_stat_reuse',result)
    result={'scope':'sealed prior full hash plus exact current size/mtime_ns/inode continuity; not a fresh full hash',
        'complete_current_shards':verified,'metadata':metadata,'GPU_tensors_yet_verified':False,
        'official_pinned_base_api_sha256':official['sha256'],
        'official_LFS_current_shard_identity_verified':True,'not_old_attention_workflow_relaunch':True,
        'current_weight_identity_reuse':reuse,'fresh_full_weight_hash_performed':False,
        'weight_bytes_read_by_identity_check':0,'after_load_stat_gate_required':True}
    write(root/'current-weight-identity.json',result)
    return verified
'''
text = text[:start] + replacement + text[end:]
old = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
new = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(text).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
changed = [name for name in old if old[name] != new[name]]
assert changed == ['validate_manifest', 'current_weight_identity'], changed
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
print({'worker_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'changed_ASTs': changed, 'run_AST_unchanged': True})
