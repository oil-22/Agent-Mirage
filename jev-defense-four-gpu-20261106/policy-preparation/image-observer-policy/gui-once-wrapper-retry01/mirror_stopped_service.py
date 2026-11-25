"""Stream private preserved evidence between servers; never save its body locally."""
import hashlib,json,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE='/home/researcher/jev-defense-four-gpu-20261106/independent-service-postexit/1793983761231132390'
DEST='/data/researcher/jev-defense-four-gpu-20261106/independent-service-postexit-mirror-1793983761231132390'
PYTHON='/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
SEAL='ae8deb5ba38b8fa86f4e853c18f70b6b9d52f70f3346cf93b7d34d1341075224'
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config']
CODE=r'''
import hashlib,json,os,sys,tarfile,time
from pathlib import Path
root=Path(DEST);assert os.getuid()==1015
root.mkdir(parents=True,exist_ok=False);root.chmod(0o700)
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|')as archive:
    for member in archive:
        relative=Path(member.name);assert not relative.is_absolute() and '..'not in relative.parts
        path=root/relative;assert path.resolve().is_relative_to(root.resolve())
        if member.isdir():path.mkdir(parents=True,exist_ok=True);continue
        assert member.isfile(),'Reject symlinks/devices from evidence stream'
        path.parent.mkdir(parents=True,exist_ok=True)
        with archive.extractfile(member)as src,path.open('xb')as dst:
            while True:
                block=src.read(1048576)
                if not block:break
                dst.write(block)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'seal.json')==EXPECTED
mapping=json.loads((root/'seal.json').read_bytes())
assert {p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p!=root/'seal.json'}==set(mapping)
for name,value in mapping.items():assert sha(root/name)==value
service=json.loads((root/'service-original-sha256.json').read_bytes())
assert {p.relative_to(root/'service').as_posix()for p in (root/'service').rglob('*')if p.is_file()}==set(service)
for name,value in service.items():assert sha(root/'service'/name)==value
assert not(root/'service/terminal-sha256.json').exists()and not(root/'service/exit.json').exists()
receipt={'stage':'exact_remote_postexit_mirror_verified','source':SOURCE,'mirror':str(root),
    'original_postexit_seal_sha256':EXPECTED,'files_verified':len(mapping),'service_files':len(service),
    'original_receipt_sha256':sha(root/'receipt.json'),'service_manifest_sha256':sha(root/'service-original-sha256.json'),
    'original_missing_terminal_not_fabricated':True,'private_full_inputs_or_auth_exported_locally':False,
    'model_GUI_HTTP_scorer_signals':0,'time':time.time()}
out=root.parent/(root.name+'-delivery');out.mkdir(exist_ok=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({'receipt.json':sha(out/'receipt.json')},indent=2),encoding='utf8')
print(json.dumps({'receipt':receipt,'delivery':str(out),'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}))
'''
CODE='DEST='+repr(DEST)+'\nSOURCE='+repr(SOURCE)+'\nEXPECTED='+repr(SEAL)+'\n'+CODE
if __name__=='__main__':
    out=ROOT/('service-postexit-mirror-invocation-'+str(time.time_ns()));out.mkdir()
    (out/'mirror-source.py').write_text(CODE,encoding='utf8')
    with (out/'source.stderr.txt').open('wb')as source_err,(out/'destination.stderr.txt').open('wb')as dest_err:
        src=subprocess.Popen(SSH+['3090','tar -C '+shlex.quote(SOURCE)+' -cf - .'],stdout=subprocess.PIPE,stderr=source_err)
        dst=subprocess.Popen(SSH+['4090',PYTHON+' -B -c '+shlex.quote(CODE)],stdin=src.stdout,stdout=subprocess.PIPE,stderr=dest_err)
        src.stdout.close()
        try:raw,_=dst.communicate(timeout=240);source_return=src.wait(timeout=30)
        except BaseException:
            dst.kill();src.kill();raise
    (out/'destination.stdout.txt').write_bytes(raw)
    if dst.returncode or source_return:raise SystemExit('Mirror transport failed; preserve partial destination')
    value=json.loads(raw)
    (out/'receipt.json').write_text(json.dumps(value,indent=2),encoding='utf8')
    (out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
    print(json.dumps({'local':str(out),**value}))
