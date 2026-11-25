"""Root-reviewed one-time upload/submission of this new finite auxiliary run."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
import sys

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT/'compact-launcher-02/frozen-compact-gpu-02'
LABELS=ROOT/'compact-launcher-02/source-first-labels-envelope-02'
OUT=ROOT/'actual-compact-four-GPU-submission-02'
REMOTE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/single-jev-9b-compact-preflight-02'
COMMAND='/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/commands/neutral-image-compact-four-preflight-02.json'
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes',
     '-o','ConnectTimeout=15','3090','python3','-']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

OUT.mkdir(exist_ok=False)
seal=json.loads((PACKAGE/'seal.json').read_bytes())
assert sha(PACKAGE/'seal.json')==sys.argv[1]
assert all(sha(PACKAGE/name)==expected for name,expected in seal.items())
assert sha(LABELS/'seal.json')=='de61cd4fce3ad5da6f36180c3fa448ba545c63abd4584479c2cd91ebd527ca5b'
assert all(sha(LABELS/row['path'])==row['sha256'] and (LABELS/row['path']).stat().st_size==row['bytes']
    for row in json.loads((LABELS/'seal.json').read_bytes())['files'])
payload=[]
for path in sorted(PACKAGE.iterdir()):
    if path.is_file():payload.append({'relative':path.name,'sha256':sha(path),'base64':base64.b64encode(path.read_bytes()).decode()})
for path in sorted(LABELS.iterdir()):
    if path.is_file():payload.append({'relative':'source-first-compact-four-peer-notes-02/'+path.name,
        'sha256':sha(path),'base64':base64.b64encode(path.read_bytes()).decode()})
spec=json.loads((PACKAGE/'launch-specification.json').read_bytes())
command=json.loads((PACKAGE/'holder-command.review-only.json').read_bytes())
assert command['script_sha256']==sha(PACKAGE/'launch_once.py')
assert command['argv'][1]==REMOTE+'/launch_once.py'
assert command['argv'][command['argv'].index('--spec-sha256')+1]==sha(PACKAGE/'launch-specification.json')
assert spec['limits']['actual_total_auxiliary_requests']==4
assert spec['limits']['automatic_format_retries']==0
write(OUT/'root-review.json',{'status':'concrete_new_compact_four_sources_reviewed',
    'package_seal_sha256':sha(PACKAGE/'seal.json'),'worker_sha256':sha(PACKAGE/'native_image_gpu_preflight.py'),
    'manifest_sha256':sha(PACKAGE/'gpu-manifest.json'),'spec_sha256':sha(PACKAGE/'launch-specification.json'),
    'root_source_label_seal_sha256':sha(LABELS/'seal.json'),'old_queue_or_terminal_restarted':False,
    'primary_model_GUI_scorer_paid_calls':0,'maximum_new_auxiliary_calls':4,
    'command_target':COMMAND,'command':command,'local_submit_source_sha256':sha(Path(__file__))})
bootstrap='''import base64,hashlib,json,os,pathlib,subprocess,time
'''
bootstrap+='target=pathlib.Path('+repr(REMOTE)+')\ncommand_target=pathlib.Path('+repr(COMMAND)+')\n'
bootstrap+='payload='+repr(payload)+'\nspec='+repr(spec)+'\ncommand='+repr(command)+'\n'
bootstrap+='''assert os.getuid()==1033
assert not target.exists() and not command_target.exists() and not command_target.with_suffix('.claimed').exists()
lease_path=pathlib.Path(spec['lease']['path']);lease_raw=lease_path.read_bytes()
assert hashlib.sha256(lease_raw).hexdigest()==spec['lease']['sha256']
lease=json.loads(lease_raw);expected=spec['expected_holder']
def identity(pid):
 p=pathlib.Path('/proc')/str(pid);tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
actual=identity(expected['pid'])
assert all(str(actual[k])==str(expected[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
held=[]
for record in lease['lock_records']:
 fd=pathlib.Path('/proc')/str(expected['pid'])/'fd'/str(record['fd'])
 info=(fd.parent.parent/'fdinfo'/str(record['fd'])).read_text()
 assert os.readlink(fd)==record['path']and fd.stat().st_ino==record['inode']
 assert 'FLOCK' in info and 'WRITE '+str(expected['pid']) in info
 held.append({'path':record['path'],'inode':fd.stat().st_ino,'fd':record['fd'],'fdinfo':info})
assert len(held)==9
cards={}
for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits']).decode().splitlines():
 index,uuid,free=[x.strip()for x in line.split(',')];cards[int(index)]={'index':int(index),'uuid':uuid,'free_mib':int(free)}
target_uuids=set()
for card in lease['gpu']:
 current=cards[card['index']];assert current['uuid']==card['uuid']and current['free_mib']>=23000
 target_uuids.add(current['uuid'])
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits']).decode().splitlines()
assert not any(line.split(',')[0].strip()in target_uuids for line in compute if line.strip())
target.mkdir(parents=True,exist_ok=False)
for row in payload:
 relative=pathlib.PurePosixPath(row['relative'])
 assert not relative.is_absolute()and '..'not in relative.parts
 path=target/row['relative'];path.parent.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode(row['base64']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
 with path.open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
stage={'holder':actual,'held_locks':held,'cards':[cards[i]for i in [4,5,6,7]],'raw_compute_rows':compute,
 'staged_files':[{k:r[k]for k in ['relative','sha256']}for r in payload],'created_unix':time.time(),'model_calls_by_submitter':0}
with(target/'root-stage-receipt.json').open('x')as stream:json.dump(stage,stream,indent=2)
with(target/'root-submission-claim.json').open('x')as stream:
 json.dump({'command_target':str(command_target),'manifest_sha256':spec['manifest']['sha256'],'time_unix':time.time()},stream)
raw=(json.dumps(command,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\\n').encode()
temporary=command_target.parent/('.neutral-publish-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno());inode=os.fstat(stream.fileno()).st_ino
os.link(temporary,command_target)
if temporary.stat().st_ino==inode:temporary.unlink()
print(json.dumps({'submitted_once':True,'command_target':str(command_target),'new_package':str(target),
 'command_sha256':hashlib.sha256(raw).hexdigest(),'fresh_holder':actual,'gpu_cards':[cards[i]for i in [4,5,6,7]],
 'maximum_auxiliary_calls':4,'primary_GUI_scorer_calls_by_submitter':0}))
'''
(OUT/'submitted-bootstrap.py').write_text(bootstrap,encoding='utf-8')
started=time.time()
result=subprocess.run(SSH,input=bootstrap.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
(OUT/'stdout.txt').write_bytes(result.stdout);(OUT/'stderr.txt').write_bytes(result.stderr)
write(OUT/'invocation.json',{'returncode':result.returncode,'started':started,'completed':time.time(),
    'bootstrap_sha256':sha(OUT/'submitted-bootstrap.py'),'no_automatic_retry':True})
write(OUT/'seal.json',{p.name:sha(p)for p in OUT.iterdir()if p.is_file()})
print(result.stdout.decode(errors='replace'))
if result.returncode:raise SystemExit(result.returncode)
