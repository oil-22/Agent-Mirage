"""Seal stopped GUI23 originals on both hosts before technical diagnosis.

All original files, including private files and native tensors, stay on their
original hosts. Export public source/requests/replies/images plus full SHA maps.
No model/GUI/scorer invocation, process signal, deletion, or retry is performed.
"""
import base64
import io
import json
from pathlib import Path
import time
import zipfile

from remote_control import HERE, ROOT3090, ROOT4090, remote, save, sha


SOURCE = r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
r=Path(ROOT);assert os.getuid()==UID
processes=[]
for relative in PROCESS_FILES:
 rec=json.loads((r/relative).read_bytes());now=identity(rec['pid'])
 assert now.get('absent')or now['state']in ['Z','X']or any(str(now[k])!=str(rec[k])for k in ['uid','command','start_ticks'])
 processes.append({'source_file':relative,'record':rec,'actual':now,'original_process_no_longer_live':True})
files={};exported={};stable={};buffer=io.BytesIO()
public_suffixes={'.json','.jsonl','.png','.image','.txt','.log','.py','.md','.diff'}
def private(name):
 parts=Path(name).parts
 return any(part.startswith('.')or'private'in part.lower()for part in parts)or Path(name).name in ['official_config.json','browser_trace.zip']
with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as archive:
 for p in sorted(r.rglob('*')):
  if not p.is_file()or p.is_symlink():continue
  before=p.stat();name=p.relative_to(r).as_posix();digest=sha(p);after=p.stat()
  assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns),name
  assert after.st_uid==UID,name
  files[name]=digest;stable[name]={'bytes':after.st_size,'inode':after.st_ino,'mtime_ns':after.st_mtime_ns,'uid':after.st_uid}
  # GUI console/auth/browser artifacts remain on host, fully hashed. Native
  # service worker.log is public model diagnostics; all request data is legal.
  public=not private(name)and p.suffix in public_suffixes and not(HOST=='4090'and p.suffix=='.log')
  if public:
   raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
   archive.writestr('output/'+name,raw);exported['output/'+name]=digest
 package=r.parent/'runtime-preparation'/r.name if HOST=='3090'else r
 manifest=json.loads((package/'manifest.json').read_bytes())
 for name,expected in manifest['files'].items():
  p=package/name;assert sha(p)==expected,name
  if 'private'in name.lower():continue
  key='frozen-source/'+name;raw=p.read_bytes();archive.writestr(key,raw);exported[key]=expected
 raw=(package/'manifest.json').read_bytes();archive.writestr('frozen-source/manifest.json',raw)
 exported['frozen-source/manifest.json']=hashlib.sha256(raw).hexdigest()
raw=buffer.getvalue()
print(json.dumps({'schema':'GUI23-postexit-original-preservation-v1','time':time.time(),'host':HOST,'original_root':str(r),
 'actual_processes':processes,'all_original_files':files,'original_file_stats':stable,
 'public_exported_files':exported,'public_archive_sha256':hashlib.sha256(raw).hexdigest(),
 'public_archive_base64':base64.b64encode(raw).decode(),'source_manifest_sha256':sha(package/'manifest.json'),
 'all_originals_retained_in_place':True,'private_auth_configs_tensors_and_browser_trace_contents_not_exported':True,
 'new_model_GPU_GUI_scorer_calls':0,'remote_read_only':True},ensure_ascii=False))
'''


def main():
    assert not (HERE / 'failure-preservation-created.json').exists()
    stamp = str(time.time_ns())
    target = HERE / ('failure-preservation-' + stamp)
    target.mkdir()
    short = HERE.parents[1] / 'j23evidence' / stamp
    short.mkdir(parents=True, exist_ok=False)
    results = {}
    for host, root, uid, process_files in [
        ('3090', ROOT3090, 1033, ['launcher-process.json', 'worker/process.json']),
        ('4090', ROOT4090, 1015, ['control/process.json', 'control/runner-process.json']),
    ]:
        prefix = 'HOST=' + repr(host) + '\nROOT=' + repr(root) + '\nUID=' + repr(uid) + '\nPROCESS_FILES=' + repr(process_files) + '\n'
        try:
            output, operation = remote(host, prefix + SOURCE, 'postexit-all-original-SHA-public-archive-before-diagnosis-' + host, timeout=55)
            record = json.loads(output)
            archive = target / (host + '-public-originals.zip')
            archive.write_bytes(base64.b64decode(record.pop('public_archive_base64'), validate=True))
            assert sha(archive) == record['public_archive_sha256']
            destination = short / host
            destination.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    path = (destination / info.filename).resolve()
                    assert path.is_relative_to(destination.resolve()) and not info.is_dir()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('xb') as stream:
                        stream.write(bundle.read(info))
                    assert sha(path) == record['public_exported_files'][info.filename]
            record.update(operation=str(operation), archive=str(archive), local_public_originals=str(destination))
            save(target / (host + '-preservation.json'), record)
            results[host] = {'receipt': str(target / (host + '-preservation.json')),
                'receipt_sha256': sha(target / (host + '-preservation.json')),
                'original_files': len(record['all_original_files']), 'public_files': len(record['public_exported_files']),
                'local_public_originals': str(destination), 'original_root': root}
        except BaseException as exc:
            save(target / (host + '-collection-failure.json'), {'type': type(exc).__name__, 'message': str(exc),
                 'originals_untouched': True, 'no_model_GUI_retry': True})
            raise
    save(target / 'receipt.json', {'time': time.time(), 'hosts': results,
        'both_original_process_groups_verified_no_longer_live': True,
        'all_original_files_stable_SHA_bound_and_retained': True, 'new_model_GUI_scorer_paid_calls': 0,
        'diagnosis_and_any_repair_must_link_this_preservation': True, 'goal': 'active'})
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    save(HERE / 'failure-preservation-created.json', {'preservation': str(target), 'receipt_sha256': sha(target / 'receipt.json'),
        'seal_sha256': sha(target / 'seal.json'), 'time': time.time()})
    print(json.dumps({'preservation': str(target), 'receipt_sha256': sha(target / 'receipt.json'), 'hosts': results,
          'originals_deleted_or_overwritten': False, 'new_model_GUI_scorer_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
