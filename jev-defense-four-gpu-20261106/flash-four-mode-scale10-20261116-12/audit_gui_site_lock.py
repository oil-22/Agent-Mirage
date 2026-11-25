"""Read-only identity, FD and kernel proof of this GUI's site lock lifecycle."""
import json
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha

CODE = r'''
import json,os,time
from pathlib import Path
p=Path(P);saved=json.loads((p/'control/process.json').read_bytes())
q=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')
st=q.stat();device=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)
matches=[]
for line in Path('/proc/locks').read_text().splitlines():
 for field in line.split():
  parts=field.split(':')
  if len(parts)!=3:continue
  try:key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
  except ValueError:continue
  if key==device:matches.append(line)
proc=Path('/proc',str(saved['pid']));actual=None;fds=[]
if proc.exists():
 s=(proc/'stat').read_text().rsplit(')',1)[1].split()
 actual={'pid':saved['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 if actual['state']not in['Z','X']:
  for fd in(proc/'fd').iterdir():
   try:
    v=fd.stat()
    if(v.st_dev,v.st_ino)==(st.st_dev,st.st_ino):fds.append(str(fd))
   except FileNotFoundError:pass
same=actual is not None and actual['state']not in['Z','X']and all(actual[k]==saved[k]for k in['uid','command','start_ticks'])
if MODE=='running':
 assert same and fds and any(int(v.split()[4])==saved['pid']for v in matches)
else:
 assert not same
 assert list(device)==EXPECTED_DEVICE
 assert not any(int(v.split()[4])==saved['pid']for v in matches)
print(json.dumps({'time':time.time(),'mode':MODE,'saved_GUI_identity':saved,'actual':actual,
 'same_original_GUI_running':same,'lock_path':str(q),'lock_device_inode':list(device),
 'original_GUI_matching_FDs':fds,'matching_kernel_locks':matches,
 'current_site_lock_free':not matches,'original_holder_absent':not same,
 'no_lock_acquired_or_resource_mutation':True,'new_model_GUI_calls':0}))
'''


def main():
    mode = sys.argv[1]
    assert mode in ['running', 'postexit']
    prior = None
    if mode == 'postexit':
        prior = json.loads((HERE / 'site-lock-running-current.json').read_bytes())
        source = Path(prior['root'])
        assert sha(source / 'seal.json') == prior['seal_sha256']
        for name, digest in json.loads((source / 'seal.json').read_bytes()).items():
            assert sha(source / name) == digest
        expected = json.loads((source / 'result.json').read_bytes())['lock_device_inode']
    else:
        expected = None
    raw, operation = remote('4090', 'P=' + repr(manifest()['package4090']) + '\nMODE=' + repr(mode) + '\nEXPECTED_DEVICE=' + repr(expected) + '\n' + CODE,
                            'actual-GUI-site-lock-' + mode)
    root = HERE / ('site-lock-' + mode + '-' + str(time.time_ns()))
    root.mkdir()
    result = {'operation': str(operation), 'running_binding': prior, **json.loads(raw)}
    save(root / 'result.json', result)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / ('site-lock-' + mode + '-current.json'), {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'mode': mode, 'original_GUI_running': result['same_original_GUI_running'],
                      'current_site_lock_free': result['current_site_lock_free'], 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
