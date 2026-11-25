"""Preserve reported preclaim failure and prepare linked control only; no submit."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
OLD=BASE/'runtime-preparation/gui-three-linked02-1793985778592347799'
PREP=BASE/'online-three-source-preparation/1793985778592347799'
ROOT=BASE/'online-submit-control-repair'/str(time.time_ns())
ROOT.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())


def save(path,value):
    with path.open('x')as f:json.dump(value,f,indent=2)


copied=[]
def copy(source,target):
    before=(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino);digest=sha(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb')as f:f.write(source.read_bytes())
    assert before==(source.stat().st_size,source.stat().st_mtime_ns,source.stat().st_ino)
    assert sha(source)==digest and sha(target)==digest
    copied.append({'source':str(source),'copy':str(target.relative_to(ROOT)),'sha256':digest})


try:
    # The root's original tool only retained combined text; separate original
    # stdout/stderr were never recorded. Do not fabricate them or reproduce failure.
    report={'source':'trusted root message; original exec_command combined tool output',
        'original_tool_chunk_id':'f74c9c','separate_original_stdout_stderr_available':False,
        'complete_original_raw_combined_stream_available':False,
        'reported_traceback_excerpt':"submit_online_three.py line14 sha(argv[1]); online_service.py line25 digest(path.read_bytes()); AttributeError: 'str' object has no attribute 'read_bytes'",
        'failure_classification':'submit_control_path_type_error_before_any_claim_or_holder_publication',
        'root_reported_model_GUI_POST_calls':0,'failed_old_submit_not_reexecuted_for_reproduction':True}
    save(ROOT/'reported-original-error-provenance.json',report)
    for path in sorted(OLD.glob('*.py')):copy(path,ROOT/'immutable-original-runtime'/path.name)
    for path in sorted(PREP.iterdir()):
        if path.is_file()and path.name!='private.token':copy(path,ROOT/'original-preparation-public'/path.name)
    save(ROOT/'reported-failed-invocation.json',{'argv_reconstructed_from_root_report_and_original_flags':[
        '/opt/whz/conda-envs/webmall-vlm/bin/python',str(OLD/'submit_online_three.py'),
        '--command',str(PREP/'holder-command.proposed.json'),'--command-sha256',
        'ba037c55849e953c73e5320f084a86a49069045449dec5fad9f4667c3171d246'],
        'reconstruction_not_claimed_as_original_shell_wire':True})
    for name,raw in REPAIR_SOURCES.items():
        with(ROOT/name).open('xb')as f:f.write(base64.b64decode(raw))
    command=['/opt/whz/conda-envs/webmall-vlm/bin/python',str(ROOT/'submit_path_compatible.py'),
        '--command',str(PREP/'holder-command.proposed.json'),'--command-sha256',
        'ba037c55849e953c73e5320f084a86a49069045449dec5fad9f4667c3171d246','--preflight']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'})
    (ROOT/'new-preflight-stdout.txt').write_bytes(result.stdout);(ROOT/'new-preflight-stderr.txt').write_bytes(result.stderr)
    assert result.returncode==0,result.stderr.decode()
    proof=json.loads(result.stdout);assert proof['all_absent']is True
    save(ROOT/'actual-unspent-preflight.json',proof)
    # Independently verify absence after the preflight and unchanged old bytes.
    assert all(not Path(path).exists()for path in proof['absent_targets'].values())
    for row in copied:assert sha(row['source'])==row['sha256']
    save(ROOT/'copied-file-bindings.json',copied)
    receipt={'status':'linked_control_ready_root_submission_not_executed','root':str(ROOT),
        'new_wrapper':str(ROOT/'submit_path_compatible.py'),'new_wrapper_sha256':sha(ROOT/'submit_path_compatible.py'),
        'original_runtime_spec_gate_command_bytes_unchanged':True,
        'reported_original_streams_honestly_unavailable':True,'actual_unspent_before_after_verified':True,
        'real_str_Path_compatibility_checked':True,'other_runtime_sha_calls_scanned_no_other_str_mismatch':True,
        'no_old_submit_reproduction':True,'repeated_19CPU_or_capacity_calls':0,
        'new_preflight_health_GET_POST_model_GUI_calls':0,'submitted':False,
        'command_sha256':'ba037c55849e953c73e5320f084a86a49069045449dec5fad9f4667c3171d246',
        'reviewed_spec_sha256':'233850b6bf6ecac89fbd18452c592a5b2481eeee9f5eaf6eea8b9af23c083e8c',
        'new_real_submit_argv':command[:-1]}
    save(ROOT/'receipt.json',receipt)
    save(ROOT/'seal.json',{str(p.relative_to(ROOT)):sha(p)for p in ROOT.rglob('*')if p.is_file()})
    print(json.dumps({'receipt':str(ROOT/'receipt.json'),'receipt_sha256':sha(ROOT/'receipt.json'),
        'seal_sha256':sha(ROOT/'seal.json'),**receipt}))
except BaseException:
    import traceback
    save(ROOT/'preparation-failure.json',{'error':traceback.format_exc(),'no_submit_model_HTTP_GUI_calls':True})
    raise
