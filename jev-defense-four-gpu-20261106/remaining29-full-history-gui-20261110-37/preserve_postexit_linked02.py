"""Seal the exited attempt and export its two failed replies; never restart it."""
import base64
import json
from pathlib import Path
import time

from orchestrate import COMMON, HERE, OUTPUT, GUIROOT, REMOTE_PACKAGE, remote, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'postexit-preservation-linked02-created.json'
    assert not pointer.exists(), 'This terminal preservation is once-only'
    terminal_pointer = json.loads((HERE / 'logical-terminal-fullhistory23-T000-stale_replace-noaux-collected.json').read_bytes())
    terminal_root = Path(terminal_pointer['collection'])
    prior_preservation = json.loads((terminal_root / 'service-preservation.json').read_bytes())
    original_request_authority = {('worker/requests/' + r['request'] + '/' + name): dict(sha256=h, stat=r['original_file_stats'][name]) for r in prior_preservation['selected_requests'] for name, h in r['original_file_SHA256'].items()}
    assert verify_seal(terminal_root) == terminal_pointer['seal_sha256']
    assert sha(terminal_root / 'receipt.json') == terminal_pointer['receipt_sha256']
    out = HERE / ('postexit-preservation-linked02-' + str(time.time_ns()))
    out.mkdir()
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'intent.json', dict(time=time.time(), original_terminal=terminal_pointer,
        two_failed_requests=['0074', '0075'], no_repair_launch_model_GUI_or_scorer=True))
    for host, root, uid, process_names, manifest_names in [
        ('3090', OUTPUT, 1033, ['launcher-process.json', 'worker/process.json'],
         ['terminal-manifest.json', 'worker/seal.json']),
        ('4090', GUIROOT, 1015, ['control/process.json', 'control/runner-process.json'],
         ['control/batch-terminal-manifest.json', 'control/seal.json']),
    ]:
        code = ('ROOT=' + repr(root) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nUID=' + repr(uid)
                + '\nPROCESS_NAMES=' + repr(process_names) + '\nMANIFEST_NAMES=' + repr(manifest_names)
                + '\nPRIOR=' + repr(original_request_authority if uid == 1033 else {}) + '\n' + COMMON + r'''
import base64
r=Path(ROOT);assert r.is_dir() and os.getuid()==UID
full_sha=sha
reused=[]
def sha(path):
 p=Path(path);key=p.relative_to(r).as_posix() if p.resolve().is_relative_to(r.resolve()) else None
 old=PRIOR.get(key)
 if old is not None and p.stat().st_size>=1048576:
  st=p.stat();actual={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino,'uid':st.st_uid}
  assert actual==old['stat'],key
  reused.append(key)
  return old['sha256']
 return full_sha(p)

processes=[]
for name in PROCESS_NAMES:
 p=r/name;record=json.loads(p.read_bytes());record=record.get('identity',record)
 actual=identity(record['pid'])
 assert actual.get('absent') or not same_live(record),name
 assert record['uid']==UID and ROOT.rsplit('/',1)[1] in record['command'],name
 processes.append({'file':name,'record':record,'actual':actual,'sha256':sha(p)})
manifests=[]
for name in MANIFEST_NAMES:
 p=r/name
 if not p.is_file():continue
 entries=json.loads(p.read_bytes())
 assert isinstance(entries,dict)
 checked=[]
 for relative,expected in entries.items():
  assert isinstance(expected,str) and len(expected)==64,(name,relative)
  # These launcher seals use paths relative to the launcher output directory.
  options=[r/relative,p.parent/relative,r/'batch'/relative]
  matches=[q for q in options if q.is_file() and q.resolve().is_relative_to(r.resolve()) and sha(q)==expected]
  assert matches,(name,relative)
  checked.append({'file':str(matches[0].relative_to(r)),'sha256':expected})
 manifests.append({'file':name,'sha256':sha(p),'full_verified_members':checked})
exports={};originals={}
def export(name):
 p=r/name
 if p.is_file():
  raw=p.read_bytes();originals[name]=sha(p);exports[name]=base64.b64encode(raw).decode()
for name in ['worker.log','exit.json','worker/terminal.json','worker/status.json',
             'control/runner.log','control/exit.json','batch/status.json',
             'terminal-manifest.json','worker/seal.json','control/seal.json',
             'control/batch-terminal-manifest.json']:
 export(name)
requests=[]
if UID==1033:
 assert (r/'exit.json').is_file() and (r/'worker/terminal.json').is_file()
 for ident in ['0074','0075']:
  folder=r/'worker/requests'/ident;seal=json.loads((folder/'seal.json').read_bytes())
  for name,expected in seal.items():assert sha(folder/name)==expected,(ident,name)
  requests.append({'request':ident,'seal_sha256':sha(folder/'seal.json'),'full_verified_files':len(seal)})
  for name in ['external-wire.json','payload.json','response.json','raw-output.txt','native-call.json',
               'effective-generation.json','actual-generation.json','prepared.json','first-forward.json','seal.json']:
   export('worker/requests/'+ident+'/'+name)
 assert len(manifests)>=1,'Original post-exit launcher seal missing'
else:
 assert (r/'control/exit.json').is_file()
 assert len(manifests)==2,'Original GUI final seals missing'
print(json.dumps({'time':time.time(),'root':ROOT,'uid':os.getuid(),'processes':processes,
 'original_manifests':manifests,'selected_requests':requests,'exported_originals':exports,
 'original_file_SHA256':originals,'read_only_no_new_calls':True,'prior_full_SHA_and_current_stat_reuse':sorted(set(reused)),'not_all_large_binaries_freshly_rehashed':True}))
''')
        output, operation = remote(host, code, 'preserve-exited-remaining29-' + host, timeout=55)
        result = json.loads(output)
        exports = result.pop('exported_originals')
        destination = out / (host + '-originals')
        destination.mkdir()
        for name, encoded in exports.items():
            target = destination / name
            assert target.resolve().is_relative_to(destination.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(encoded, validate=True))
            assert sha(target) == result['original_file_SHA256'][name]
        save(out / (host + '.json'), dict(result, remote_operation=str(operation)))
    save(out / 'receipt.json', dict(time=time.time(), original_terminal=terminal_pointer,
        all_verified_originals_preserved=True, original_sources_and_logs_retained_in_place=True,
        original_observer_timeout_preserved='postexit-preservation-1794305670969484100',
        prior_full_original_request_SHA_authority=terminal_pointer,
        large_originals_reuse_prior_full_SHA_plus_current_stat_not_new_full_hash=True,
        no_terminal_retry_or_mutation=True, new_model_GUI_capture_action_scorer_calls=0))
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    result = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
