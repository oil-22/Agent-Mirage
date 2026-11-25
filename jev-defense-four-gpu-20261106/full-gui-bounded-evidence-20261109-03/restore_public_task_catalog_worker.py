"""CPU archive restoration only; no trace outputs, answer export or model calls."""
from pathlib import Path,PurePosixPath
import argparse
import gzip
import hashlib
import json
import os
import subprocess
import tarfile
import time
import traceback

ARCHIVE=Path('/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz')
PREFIX='mirage-trace/_shared/VisualWebArena__all-configurations/vwa100-2026-10-09/selected100-classifieds-reddit-v2/evaluator_configs_v1/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def main(root):
    assert os.getuid()==1015 and os.environ['CUDA_VISIBLE_DEVICES']==''
    root.mkdir(exist_ok=False);private=root/'PRIVATE-evaluator-configs';private.mkdir(mode=0o700)
    identity={'pid':os.getpid(),'uid':os.getuid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
        'full_command':Path('/proc/self/cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()}
    save(root/'process.json',identity)
    targets={}
    with gzip.open('/data/researcher/attention-audit-20261031/members.jsonl.gz','rt')as f:
        for line in f:
            row=json.loads(line);name=row[0]
            if name.startswith(PREFIX)and PurePosixPath(name).name.startswith('classifieds_')and name.endswith('.json'):
                assert row[2]=='0','Expected direct immutable shared source, never guessed link target'
                targets[name]=row
    assert len(targets)>=50
    save(root/'selection-before-archive-read.json',{'selection':'ALL original shared classifieds config sources; no output/outcome selection',
        'members':targets,'export_fields_only':['task_id','intent','image','sites','require_reset'],
        'evaluation_fields_private':True,'source_body_sha256':sha(Path(__file__))})
    initial=ARCHIVE.stat();started=time.time();rows=[];error=None;proc=None
    try:
        with(root/'decompress.log').open('xb')as log:
            proc=subprocess.Popen(['pigz','-p','2','-dc',str(ARCHIVE)],stdout=subprocess.PIPE,stderr=log)
            try:
                with tarfile.open(fileobj=proc.stdout,mode='r|')as archive:
                    for member in archive:
                        if member.name not in targets:continue
                        assert member.isfile()and member.size==targets[member.name][1]
                        name=PurePosixPath(member.name);assert not name.is_absolute()and'..'not in name.parts
                        raw=archive.extractfile(member).read();value=json.loads(raw)
                        p=private/(name.stem+'.PRIVATE.json');p.write_bytes(raw);p.chmod(0o600)
                        public={key:value.get(key)for key in ['task_id','intent','image','sites','require_reset']}
                        public.update(source_member=member.name,source_config_sha256=sha(p),
                            private_evaluator_fields_exported=False,not_experiment_results=True)
                        rows.append(public)
                        save(root/('source-progress-%03d.json'%len(rows)),{'collected':len(rows),'expected':len(targets),'latest_task_name':name.stem,'models_GUI_calls':0})
                        if len(rows)==len(targets):break
            finally:
                if proc.poll()is None:proc.terminate()
                proc.wait(timeout=20)
        assert len(rows)==len(targets),'Incomplete source restoration is not a full task catalog'
        after=ARCHIVE.stat();assert(initial.st_size,initial.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        save(root/'public-task-catalog.json',{'tasks':sorted(rows,key=lambda r:(r['task_id']if isinstance(r['task_id'],int)else str(r['task_id']))),
            'source_archive':str(ARCHIVE),'source_archive_bytes':initial.st_size,'not_official_provenance_or_model_results':True,
            'private_answers_never_model_input':True,'models_GUI_scorer_calls':0})
    except BaseException:error=traceback.format_exc();save(root/'failure.json',{'traceback':error,'no_automatic_retry':True})
    finally:
        save(root/'receipt.json',{'status':'complete'if error is None else'technical_failure','tasks':len(rows),'expected':len(targets),
            'source_archive':str(ARCHIVE),'initial_size':initial.st_size,'initial_mtime_ns':initial.st_mtime_ns,
            'source_worker_sha256':sha(Path(__file__)),'models_GUI_scorer_calls':0,'private_evaluator_fields_exported':False,
            'seconds':time.time()-started,'error':error})
        save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
    return 1 if error else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();raise SystemExit(main(a.output))
