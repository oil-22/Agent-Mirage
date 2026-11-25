"""Copy only SHA-verified partial files to a NEW mirror, then stream missing bytes."""
import hashlib,importlib.util,json,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('mirror_original',HERE/'mirror_stopped_service.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
DEST=old.DEST+'-gzip-linked02'
PARTIALS=[old.DEST,old.DEST+'-gzip-linked01']
manifest=json.loads((ROOT/'service-postexit-preservation-invocation-1793983751091430900/seal.json').read_bytes())
manifest['seal.json']=old.SEAL
out=ROOT/('service-postexit-gzip02-mirror-invocation-'+str(time.time_ns()));out.mkdir()
SETUP='DEST='+repr(DEST)+'\nPARTIALS='+repr(PARTIALS)+'\nEXPECTED='+repr(manifest)+'\n'+r'''
import hashlib,json,shutil
from pathlib import Path
root=Path(DEST);root.mkdir(exist_ok=False);root.chmod(0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
copied=[];missing=[]
for name,value in EXPECTED.items():
    rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts and '\n'not in name
    valid=None
    for base in PARTIALS:
        candidate=Path(base)/rel
        if candidate.is_file()and not candidate.is_symlink()and sha(candidate)==value:
            valid=candidate;break
    if valid is None:missing.append(name);continue
    target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(valid,target);assert sha(target)==value
    copied.append(name)
print(json.dumps({'new_root':DEST,'old_partials_untouched':PARTIALS,'valid_files_copied':len(copied),
    'missing_files':missing,'new_bytes_copied_on_same_server':sum((root/n).stat().st_size for n in copied)}))
'''
(out/'setup-source.py').write_text(SETUP,encoding='utf8')
setup=subprocess.run(old.SSH+['4090',old.PYTHON+' -B -'],input=SETUP,capture_output=True,text=True,timeout=90)
(out/'setup.stderr.txt').write_text(setup.stderr,encoding='utf8')
(out/'setup.stdout.txt').write_text(setup.stdout,encoding='utf8')
if setup.returncode:raise SystemExit(setup.returncode)
prepared=json.loads(setup.stdout);missing=prepared['missing_files']
CODE=old.CODE.replace(repr(old.DEST),repr(DEST)).replace("mode='r|'","mode='r|gz'")
CODE=CODE.replace('root.mkdir(parents=True,exist_ok=False);root.chmod(0o700)',
    "assert root.exists() and not root.is_symlink();root.chmod(0o700)")
(out/'mirror-source.py').write_text(CODE,encoding='utf8')
(out/'link.json').write_text(json.dumps({'prior_partial_attempts_preserved':PARTIALS,
    'source_root':old.SOURCE,'expected_original_seal_sha256':old.SEAL,'new_root':DEST,
    'only_transport_change':'new exact mirror reuses SHA-verified copies; streams missing gzip entries',
    'timeout_seconds':900,'new_model_GUI_HTTP_scorer_signals':0},indent=2),encoding='utf8')
with (out/'source.stderr.txt').open('wb')as srcerr,(out/'destination.stderr.txt').open('wb')as dsterr:
    command='tar -C '+shlex.quote(old.SOURCE)+' --no-recursion -czf - -T -'
    src=subprocess.Popen(old.SSH+['3090',command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=srcerr)
    dst=subprocess.Popen(old.SSH+['4090',old.PYTHON+' -B -c '+shlex.quote(CODE)],stdin=src.stdout,stdout=subprocess.PIPE,stderr=dsterr)
    src.stdout.close();src.stdin.write(('\n'.join(missing)+'\n').encode());src.stdin.close()
    try:raw,_=dst.communicate(timeout=900);source_return=src.wait(timeout=30)
    except BaseException:
        dst.kill();src.kill();raise
(out/'destination.stdout.txt').write_bytes(raw)
if dst.returncode or source_return:raise SystemExit('Linked02 mirror failed; keep partial')
value=json.loads(raw)
(out/'receipt.json').write_text(json.dumps({'transport_setup':prepared,**value},indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),'transport_reused_valid_files':prepared['valid_files_copied'],
    'transport_streamed_files':len(missing),**value}))
