"""New linked submit entrypoint; immutable original module retains its __file__.

The only execution-time override is original_submit.sha(value)->native_sha(Path(value)).
Original worker, admission, claim, atomic publisher, gate and command stay unchanged.
Only root invokes the submission mode; --preflight makes no claim or publication.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

OLD=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/gui-three-linked02-1793985778592347799')
PREP=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-source-preparation/1793985778592347799')
ORIGINAL_SHA='4d9830ec1d3565573800ba120ac663f3822dd192fa39a097d20774bbaebf2f50'
COMMAND_SHA='ba037c55849e953c73e5320f084a86a49069045449dec5fad9f4667c3171d246'
SPEC_SHA='233850b6bf6ecac89fbd18452c592a5b2481eeee9f5eaf6eea8b9af23c083e8c'


def load_original():
    import hashlib
    path=OLD/'submit_online_three.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ORIGINAL_SHA:
        raise RuntimeError('Immutable original submit module differs')
    sys.path.insert(0,str(OLD))
    definition=importlib.util.spec_from_file_location('sealed_original_submit_online_three',path)
    module=importlib.util.module_from_spec(definition);definition.loader.exec_module(module)
    original_sha=module.sha
    module.sha=lambda value:original_sha(Path(value))
    if Path(module.__file__).resolve()!=path.resolve():
        raise RuntimeError('Original here/entrypoint context changed')
    return module


def check(a,module):
    if a.command.resolve()!=(PREP/'holder-command.proposed.json').resolve() or a.command_sha256!=COMMAND_SHA:
        raise RuntimeError('Only the exact originally reviewed holder command is admitted')
    if module.sha(a.command)!=COMMAND_SHA or module.sha(str(a.command))!=COMMAND_SHA:
        raise RuntimeError('Actual str/Path hashing does not match original command')
    command=module.read(a.command);argv=command['argv']
    if command['action']!='launch' or Path(argv[1])!=OLD/'launch_online_group.py' or module.sha(argv[1])!=command['script_sha256']:
        raise RuntimeError('Sealed original launch command differs')
    path=Path(argv[argv.index('--spec')+1]);expected=argv[argv.index('--spec-sha256')+1]
    if path!=PREP/'launch-specification.reviewed.json' or expected!=SPEC_SHA or module.sha(path)!=SPEC_SHA:
        raise RuntimeError('Sealed originally reviewed runtime spec differs')
    spec=module.read(path)
    if spec['root_reviewed_approval'] is not True:raise RuntimeError('Root-reviewed original spec required')
    module.validate_static(spec,OLD);sys.path.insert(0,spec['preflight_source_root'])
    from capacity_gate import verify_manifest,validate_old_terminal,empty_resources,identity,same
    gate,proof,old=module.verify_gate(spec,verify_manifest,validate_old_terminal,identity,same)
    lease=module.read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    resources=empty_resources(lease)
    target=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/commands')/('online-three-'+Path(spec['new_group']).name+'.json')
    names={'new_group':Path(spec['new_group']),'once_only_claim':Path(spec['once_only_claim']),
        'submission_claim':Path(spec['submission_claim']),'holder_target_command':target}
    if any(path.exists()for path in names.values()):
        raise RuntimeError('Prior claim/publication/group detected; no automatic submission retry')
    return {'status':'preflight_passed_not_submitted','time':time.time(),
        'old_module_sha256':ORIGINAL_SHA,'command_sha256':COMMAND_SHA,'reviewed_spec_sha256':SPEC_SHA,
        'str_and_Path_real_file_hash_equal':True,'original_module_here_retained':True,
        'original_runtime_source_gate_command_unchanged':True,
        'absent_targets':{key:str(value)for key,value in names.items()},
        'all_absent':True,'new_group_model_requests':0,'new_group_transitions':0,
        'resources':resources,'old_terminal_preserved':old,'health_GET_POST_model_GUI_calls':0}


def main(a):
    module=load_original();proof=check(a,module)
    if a.preflight:
        print(json.dumps(proof));return
    # This is the root's real invocation. It does not re-run the old failed
    # control entrypoint: the new wrapper supplies the path-compatible hash.
    # All original claim/resource/no-clobber admission remains in module.main.
    module.main(a)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--command',type=Path,required=True)
    p.add_argument('--command-sha256',required=True);p.add_argument('--preflight',action='store_true')
    main(p.parse_args())
