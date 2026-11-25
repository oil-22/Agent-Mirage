"""New linked gzip transport; preserve the earlier timed-out raw destination."""
import hashlib,importlib.util,json,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
prior=HERE/'mirror_stopped_service.py'
spec=importlib.util.spec_from_file_location('prior_mirror_source',prior)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
DEST=old.DEST+'-gzip-linked01'
CODE=old.CODE.replace(repr(old.DEST),repr(DEST)).replace("mode='r|'","mode='r|gz'")
out=ROOT/('service-postexit-gzip-mirror-invocation-'+str(time.time_ns()));out.mkdir()
(out/'mirror-source.py').write_text(CODE,encoding='utf8')
(out/'prior-source.py').write_bytes(prior.read_bytes())
(out/'link.json').write_text(json.dumps({'prior_destination_preserved':old.DEST,
    'prior_attempt_status':'transport_timeout_240_seconds_not_integrity_or_model_result',
    'new_destination':DEST,'only_transport_change':'tar gzip stream; exact decompressed bytes remain SHA-verified',
    'prior_source_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),
    'new_model_GUI_HTTP_scorer_signals':0},indent=2),encoding='utf8')
with (out/'source.stderr.txt').open('wb')as source_err,(out/'destination.stderr.txt').open('wb')as dest_err:
    src=subprocess.Popen(old.SSH+['3090','tar -C '+shlex.quote(old.SOURCE)+' -czf - .'],stdout=subprocess.PIPE,stderr=source_err)
    dst=subprocess.Popen(old.SSH+['4090',old.PYTHON+' -B -c '+shlex.quote(CODE)],stdin=src.stdout,stdout=subprocess.PIPE,stderr=dest_err)
    src.stdout.close()
    try:raw,_=dst.communicate(timeout=240);source_return=src.wait(timeout=30)
    except BaseException:
        dst.kill();src.kill();raise
(out/'destination.stdout.txt').write_bytes(raw)
if dst.returncode or source_return:raise SystemExit('Linked mirror transport failed; preserve partial destination')
value=json.loads(raw)
(out/'receipt.json').write_text(json.dumps(value,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),**value}))
