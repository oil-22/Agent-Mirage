"""Offline-only bootstrap: real human approval and live locks precede imports/load.

This file has no automatic launch, HTTP service, Flash call, browser, evaluator,
baseline generation, resume, or extra capacity generation path.
"""
import copy
import hashlib
import json
import os
import signal
import sys
from pathlib import Path

import runtime_guard as guard
from offline_protocol import canonical, digest, require, run_offline, save, validate_authorization
import reading_contract as contract
from checked_native_call import audited_generate, compare_records, tensor_records

P = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_bytes())


def validate_package(approval_path, approval_sha):
    manifest = load(P / 'execution-manifest.json')
    for name, expected in manifest['files'].items():
        require(guard.sha(P / name) == expected, 'Prepared package file changed: ' + name)
    require(guard.sha(approval_path) == approval_sha, 'Human reply receipt file changed')
    authorization = load(approval_path)
    validate_authorization(authorization, manifest['proposal_seal_sha256'])
    require(authorization['study_claim_root'] == manifest['study_claim_root'], 'Study claim path changed')
    require(manifest['actual_new_model_GUI_calls_in_preparation'] == 0, 'Wrong source preparation')
    return manifest, authorization


def bind_cases(manifest):
    cases = []
    for row in manifest['cases']:
        cid = row['case_id']
        original_root = Path(row['original_request'])
        require(guard.sha(original_root / 'seal.json') == row['original_request_seal_sha256'], 'Original request seal changed')
        original_seal = load(original_root / 'seal.json')
        for name in ['body.json', 'wire-request.bin', 'effective-generation.json']:
            require(guard.sha(original_root / name) == original_seal[name], 'Original source member changed: ' + name)
        require(guard.sha(original_root / 'body.json') == row['original_body_file_sha256'], 'Original complete body file changed')
        original, wire = load(original_root / 'body.json'), load(original_root / 'wire-request.bin')
        require(wire['body'] == original and wire['request_id'] == row['original_request_id'], 'Source request mismatch')
        wrapper = load(P / row['CPU_wrapper'])
        remote = Path(wrapper['remote_case'])
        require(guard.sha(remote / 'seal.json') == wrapper['remote_seal_sha256'], 'Prepared native CPU seal changed')
        for name, expected in load(remote / 'seal.json').items():
            require(guard.sha(remote / name) == expected, 'Prepared native CPU file changed: ' + name)
        cpu = load(remote / 'result.json')
        require(cpu == wrapper['result'], 'Wrapper and sealed native CPU result differ')
        body, binding = load(remote / 'preread-full-body.json'), load(remote / 'source-binding.json')
        require(guard.sha(remote / 'preread-full-body.json') == row['preread_body_file_sha256'], 'Prepared preread file changed')
        require(guard.sha(remote / 'source-binding.json') == row['source_binding_file_sha256'], 'Prepared source map changed')
        expected_body, expected_binding = contract.project_source(original)
        require(body == expected_body and binding == expected_binding, 'Image-only source projection changed')
        config = load(P / row['original_generation_file'])
        require(config == load(original_root / 'effective-generation.json'), 'Original effective generation changed')
        cases.append({'case_id': cid, 'original_body': original, 'binding': binding, 'preread_body': body,
                      'original_effective_generation': config, 'frozen_preread_CPU': cpu['prepared']})
    return cases


def main():
    require(len(sys.argv) == 3, 'Explicit real authorization file and SHA required')
    manifest, authorization = validate_package(Path(sys.argv[1]), sys.argv[2])
    require(os.getuid() == 1033, 'Wrong owned-task UID')
    cases = bind_cases(manifest)
    stopped = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopped.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: stopped.__setitem__(0, True))
    worker_root = Path(manifest['output']) / 'worker'
    worker_root.mkdir(exist_ok=False)
    save(worker_root / 'process.json', guard.identity(os.getpid()))
    native, installed = [None], [None]

    def resources(loaded):
        require(not stopped[0], 'Manual stop; no automatic continuation')
        return guard.resource(loaded)

    def cpu_prepare(body, folder):
        if native[0] is None:
            # No model imports/loading before real authorization, global once
            # claim, immutable input bindings, and inherited-lock admission.
            resources(False)
            import primary_server
            from memory_installer import install_previous_memory_implementation
            primary_server.resource = resources
            native[0] = primary_server.NativeActor(worker_root)
            installed[0] = install_previous_memory_implementation(native[0], worker_root, manifest)
        import base64
        import io
        from PIL import Image
        torch = native[0].torch
        converted = []
        for message in body['messages']:
            parts = message['content'] if isinstance(message['content'], list) else [{'type':'text','text':message['content']}]
            blocks = []
            for block in parts:
                if block['type'] == 'text':
                    blocks.append(copy.deepcopy(block))
                elif block['type'] == 'image_url':
                    url = block['image_url']['url']
                    require(url.startswith('data:image/png;base64,'), 'Only complete original PNGs')
                    blocks.append({'type':'image','image':Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1],validate=True))).convert('RGB')})
                else:
                    raise ValueError('Unknown original input block')
            converted.append({'role':message['role'],'content':blocks})
        inputs = native[0].engine.processor.apply_chat_template(converted, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors='pt', tools=body.get('tools'), **body.get('chat_template_kwargs',{}))
        require(all(value.device.type == 'cpu' for value in inputs.values()), 'Input preparation must stay on CPU')
        records = tensor_records(torch, inputs)
        case = next(c for c in cases if c['case_id'] == folder.parent.name)
        if folder.name == 'preread':
            compare_records(records, case['frozen_preread_CPU'])
        else:
            non_visual = {'input_ids','attention_mask','position_ids','token_type_ids','mm_token_type_ids'}
            compare_records({k:v for k,v in records.items() if k not in non_visual},
                            {k:v for k,v in case['frozen_preread_CPU'].items() if k not in non_visual})
        save(folder / 'source-binding.json', {'source_map':case['binding'],
             'body_canonical_sha256':digest(canonical(body)), 'dynamic_actor_CPU_before_actual_generation':folder.name=='actor',
             'no_history_or_image_truncation':True, 'not_a_GPU_capacity_test':True})
        return records

    def generate(body, folder, expected, original_generation, cap):
        implementation = installed[0]
        require(implementation[0].__code__ is implementation[1] and implementation[2].__code__ is implementation[3],
                'Previously validated memory implementation replaced')
        return audited_generate(native[0], body, folder, expected, original_generation, cap, resources)

    terminal = run_offline(root=Path(manifest['study_claim_root']) / 'attempt01',
        study_claim_root=manifest['study_claim_root'], authorization=authorization,
        proposal_seal_sha256=manifest['proposal_seal_sha256'], cases=cases, contract=contract,
        native_cpu_prepare=cpu_prepare, resource_admission=resources, audited_native_call=generate)
    save(worker_root / 'terminal-reference.json', {'terminal':str(Path(manifest['study_claim_root'])/'attempt01/terminal.json'),
         'status':terminal['status'], 'attempted_calls':len(terminal['attempted']), 'maximum_calls':20,
         'reserved_GPU_count':8, 'new_GUI_Flash_scorer_paid_calls':0, 'formal_GUI_release':False})
    return 0 if terminal['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
