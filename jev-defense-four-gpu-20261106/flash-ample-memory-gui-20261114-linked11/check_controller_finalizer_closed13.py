"""Exercise finalizer bindings on13 immutable completed runs; not final29 audit."""
import json
import time
from pathlib import Path
from control import HERE, R4090, remote, save, sha
from capture_live_evidence import COMMON
from finalize_GUI_controller_bindings import GUI_READER, check_controller, parse_original


def main():
    evidence = HERE / 'live-evidence-incremental-1794662012451421800'
    terminals_path = HERE / 'terminal-audit-1794660596803440200.json'
    assert all(sha(evidence / n) == h for n, h in json.loads((evidence / 'seal.json').read_bytes()).items())
    terminals = {v['run']['run_id']: v for v in json.loads(terminals_path.read_bytes())['result']['terminals']}
    assert len(terminals) == 13
    template = GUI_READER.replace(
        "a=terminal_path.parent;t=json.loads(terminal_path.read_bytes());seal=json.loads((a/'seal.json').read_bytes())",
        "a=terminal_path.parent;t=json.loads(terminal_path.read_bytes())\n if t['run']['run_id']not in EXPECTED:continue\n seal=json.loads((a/'seal.json').read_bytes())")
    old = "assert len(controllers)==29 and {v['terminal']['run']['run_id']for v in controllers}=={v['run_id']for v in plan['queue']}"
    assert template.count(old) == 1
    template = template.replace(old, "assert len(controllers)==13 and {v['terminal']['run']['run_id']for v in controllers}==set(EXPECTED)")
    raw, operation = remote('4090', 'ROOT=' + repr(R4090) + '\nEXPECTED=' + repr(sorted(terminals)) + '\n' + COMMON + template,
                            'controller-finalizer-original13-closed-development', timeout=55)
    gui = json.loads(raw)
    native = json.loads((evidence / '3090.json').read_bytes())
    mains = {v['request_id']: v for v in native['sealed_main_requests']}
    flashes = {v['request_id']: v for v in native['sealed_Flash_requests']}
    parse = parse_original()
    rows = [check_controller(v, mains, flashes, terminals[v['terminal']['run']['run_id']], parse)
            for v in gui['controllers']]
    dest = HERE / ('controller-finalizer-closed13-development-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'GUI-collection.json', {'result': gui, 'operation': str(operation)})
    save(dest / 'result.json', {'time': time.time(), 'completed_runs_checked': len(rows),
         'native_requests_checked': sum(len(v['actor_requests']) for v in rows),
         'Flash_requests_checked': sum(len(v['Flash_requests']) for v in rows),
         'rows': rows, 'native_audit': str(evidence), 'native_audit_seal_sha256': sha(evidence / 'seal.json'),
         'terminal_audit': str(terminals_path), 'terminal_audit_sha256': sha(terminals_path),
         'finalizer_source_sha256': sha(HERE / 'finalize_GUI_controller_bindings.py'),
         'original_raw_native_checks_referenced_at_original_times': True,
         'raw_full_tensors_rehashed_by_this_check': False,
         'original29_postexit_final_audit_executed': False,
         'semantic_labels_or_effectiveness_proved': False, 'current_runtime_sources_changed': False,
         'new_model_GPU_GUI_calls': 0})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'development_check': str(dest), 'completed_runs': 13,
                      'main_requests_bound': sum(len(v['actor_requests']) for v in rows),
                      'actual_final29_postexit_audit': False, 'new_model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
