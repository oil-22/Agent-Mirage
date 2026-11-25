"""Seal transport preparation plus one actual noaux cross-host compatibility.

This does not rerun a control or change any runtime source. The enabled mixed
native/HTTP/GPU/Controller end-to-end branch still needs an actual invocation.
"""
import base64
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from orchestrate import COMMON, OUTPUT, GUIROOT, REMOTE_PACKAGE, remote, save, sha
from check_mixed_exchange_audit import run_checks


def verified_folder(path):
    path = Path(path)
    for name, expected in json.loads((path / "seal.json").read_bytes()).items():
        assert sha(path / name) == expected, str(path / name)


def main():
    pointer = HERE / "mixed-exchange-audit-preparation-created.json"
    assert not pointer.exists()
    package = HERE / "runtime-package"
    manifest_sha = sha(package / "manifest.json")
    manifest = json.loads((package / "manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        assert sha(package / name) == expected, name
    # This is an existing, source-reviewed original actor invocation. Its native
    # input/output audit is linked, not counted again as another completed call.
    native_pointer = json.loads((HERE / "new-replies-37-audit-created.json").read_bytes())
    native_path = Path(native_pointer["audit"])
    verified_folder(native_path.parent)
    assert sha(native_path) == native_pointer["audit_sha256"]
    native_audit = json.loads(native_path.read_bytes())
    native = next(row for row in native_audit["requests"] if row["request"] == "0063")
    assert native_audit["passed"] and native["operation"] == "actor" and native["natural_EOS"]
    authority = next(row for row in native_audit["selected_binary_full_SHA_authorities"] if row["request"] == "0063")
    verified_folder(authority["evidence"])
    service_snapshot = json.loads((Path(authority["evidence"]) / "3090.json").read_bytes())
    sealed = next(row for row in service_snapshot["sealed_requests"] if row["request"] == "0063")
    assert sealed["files_verified"] > 0 and sealed["seal_sha256"] == authority["request_seal_sha256"]
    source_packet_path = HERE / "source-first-packets/1794241645846373900/f11d16e2aaae5789bb11/packet.json"
    verified_folder(source_packet_path.parent.parent)
    source_packet = json.loads(source_packet_path.read_bytes())
    helper = (HERE / "mixed_exchange_checks.py").read_text(encoding="utf8")
    mapper = (HERE / "mixed_journal_map.py").read_text(encoding="utf8")
    out = HERE / ("mixed-exchange-audit-preparation-" + str(time.time_ns()))
    out.mkdir()
    for name in ["mixed_exchange_checks.py", "check_mixed_exchange_audit.py", "prepare_mixed_exchange_audit.py"]:
        (out / name).write_bytes((HERE / name).read_bytes())
    try:
        checks = run_checks()
        save(out / "CPU-checks.json", {"passed": True, "count": len(checks), "checks": checks,
            "synthetic_derived_fixtures_not_new_model_or_GUI_controls": True})
        code = ("ROOT=" + repr(OUTPUT) + "\nPACKAGE=" + repr(REMOTE_PACKAGE) +
            "\nMANIFEST_SHA=" + repr(manifest_sha) + "\nMAPPER=" + repr(mapper) +
            "\nEXPECTED_SEAL=" + repr(authority["request_seal_sha256"]) + "\n" + COMMON + r'''
r=Path(ROOT);package=Path(PACKAGE)
assert os.getuid()==1033 and sha(package/'manifest.json')==MANIFEST_SHA
ns={'__name__':'read_only_full_worker_journal_mapping'}
exec(compile(MAPPER,'readonly-mixed-journal-mapper','exec'),ns)
raw=(r/'worker/journal/events.jsonl').read_bytes()
events,chain=ns['verified_events'](raw)
plan=json.loads((package/'plan.json').read_bytes())
carry=json.loads((package/'carryover/state.json').read_bytes())
mapped=ns['map_requests'](events,plan['queue'],carry['initial_transport_counts'])
row=next(item for item in mapped['sealed_requests']if item['request']=='0063')
assert row['operation']=='actor' and row['seal_sha256']==EXPECTED_SEAL
assert row['primary_prefill_session']==63
p=r/'worker/requests/0063';assert sha(p/'seal.json')==EXPECTED_SEAL
seal=json.loads((p/'seal.json').read_bytes())
for name in ['external-wire.json','payload.json','response.json']:
 assert sha(p/name)==seal[name],name
wire=(p/'external-wire.json').read_bytes();body=json.loads(wire)
assert ns['canonical'](body)==wire
payload=json.loads((p/'payload.json').read_bytes())
assert payload==body['payload']
response=json.loads((p/'response.json').read_bytes())
binding={'wire_sha256':hashlib.sha256(wire).hexdigest(),'payload_sha256':hashlib.sha256(ns['canonical'](payload)).hexdigest(),
 'request_id':body['request_id'],'request_seal_sha256':EXPECTED_SEAL,
 'response_raw_sha256':hashlib.sha256(ns['canonical'](response)).hexdigest(),'response':response,'receipt':str(p),
 'actual_actor_body_sha256':hashlib.sha256(ns['canonical'](payload['body'])).hexdigest()}
assert binding['payload_sha256']==row['payload_sha256']
run=next(item for item in plan['queue']if item['run_id']==row['trajectory_id'])
assert run['observer_enabled'] is False
prefill=r/'worker'/('prefill-residency-%03d.json'%row['primary_prefill_session'])
proof=json.loads(prefill.read_bytes())
assert proof['session']==63 and proof['success'] is True and proof['full_GPU_resident_before_decode'] is True
print(json.dumps({'request_map':row,'binding':binding,'worker_chain':chain,'frozen_queue_run':run,
 'manifest_sha256':MANIFEST_SHA,'prefill_file':str(prefill),'prefill_file_sha256':sha(prefill),
 'read_only':True,'new_model_GUI_scorer_calls':0}))
''')
        output, operation3090 = remote("3090", code, "read-only-actor35-server-transport-binding", timeout=55)
        service = json.loads(output)
        save(out / "3090-server-bindings.json", service)
        assert service["binding"]["actual_actor_body_sha256"] == source_packet["actor_request_body_sha256"]
        assert service["request_map"]["decision"] == native["decision"] == 35
        code = ("ROOT=" + repr(GUIROOT) + "\nMANIFEST_SHA=" + repr(manifest_sha) +
            "\nSERVER=" + repr(service) + "\nHELPER=" + repr(helper) + "\n" + COMMON + r'''
import base64,sys
r=Path(ROOT);assert os.getuid()==1015 and sha(r/'manifest.json')==MANIFEST_SHA
manifest=json.loads((r/'manifest.json').read_bytes())
for name in ['release/image_evidence.py','release/evidence_observer.py','release/intrinsic_count_guard.py','actor-template.json']:
 assert sha(r/name)==manifest['files'][name],name
sys.path.insert(0,str(r/'release'))
from image_evidence import ACTOR_BOUNDARY,canonical,digest
from evidence_observer import NeutralEvidenceObserver
ns={'__name__':'read_only_cross_host_exchange_checks'}
exec(compile(HELPER,'readonly-mixed-exchange-checks','exec'),ns)
target_id=SERVER['binding']['request_id'];matches=[];snapshots=[]
for path in sorted((r/'batch/runs').glob('*/attempt-*/events.jsonl')):
 previous='0'*64;count=0;complete_bytes=0;prefix_hash=hashlib.sha256();current=[];target=False
 incomplete_bytes=0;incomplete_sha=None
 with path.open('rb')as stream:
  for raw in stream:
   if not raw.endswith(b'\n'):
    incomplete_bytes=len(raw);incomplete_sha=digest(raw);break
   value=json.loads(raw);event=dict(value);signature=event.pop('sha256')
   assert value['seq']==count and value['previous']==previous and digest(canonical(event))==signature
   previous=signature;count+=1;complete_bytes+=len(raw);prefix_hash.update(raw)
   kind=value['kind']
   if kind=='actor_request':current=[value];target=False
   elif kind in ['neutral_evidence_packet','neutral_evidence_actor_insertion']:
    if current:current.append(value)
   elif kind=='actual_actor_wire_request':
    target=value['data']['body']['request_id']==target_id
    if target:current.append(value)
   elif target and kind in ['actual_actor_wire_raw_response','actual_actor_wire_response']:
    current.append(value)
    if kind=='actual_actor_wire_response':matches.append((str(path),list(current)))
 snapshots.append({'path':str(path),'events':count,'head':previous,'complete_prefix_bytes':complete_bytes,
  'complete_prefix_sha256':prefix_hash.hexdigest(),'incomplete_tail_bytes':incomplete_bytes,'incomplete_tail_sha256':incomplete_sha})
assert len(matches)==1
path,events=matches[0]
assert [e['kind']for e in events]==['actor_request','neutral_evidence_packet','neutral_evidence_actor_insertion',
 'actual_actor_wire_request','actual_actor_wire_raw_response','actual_actor_wire_response']
context,packet,insertion,wire,raw_response,response=events
http=ns['check_http_exchange'](request_event=wire,raw_response_event=raw_response,response_event=response,
 server_binding=SERVER['binding'],mapped_request=SERVER['request_map'])
observer=NeutralEvidenceObserver(None,model='Qwen/Qwen3.5-9B',revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',enabled=False,max_calls=60)
expected=observer.packet(None)
template=json.loads((r/'actor-template.json').read_bytes())
insert=ns['check_actor_insertion'](context_event=context,packet_event=packet,insertion_event=insertion,
 actor_request_event=wire,actor_template=template,actor_boundary=ACTOR_BOUNDARY,
 expected_packet=expected,observer_enabled=False)
assert SERVER['frozen_queue_run']['observer_enabled']is False
assert 'torch'not in sys.modules,'Read-only transport checker unexpectedly imported model runtime'
print(json.dumps({'passed':True,'HTTP':http,'actor_insertion':insert,'GUI_journal_snapshots':snapshots,
 'selected_event_SHA256':{e['kind']:e['sha256']for e in events},'selected_journal':path,
 'no_model_weights_loaded':True,'no_CUDA_initialization':True,'new_model_GUI_scorer_calls':0}))
''')
        output, operation4090 = remote("4090", code, "read-only-actor35-HTTP-fullhistory-insertion-binding", timeout=55)
        gui = json.loads(output)
        save(out / "4090-GUI-bindings.json", gui)
        assert gui["passed"] and gui["selected_event_SHA256"]["actor_request"] == source_packet["actor_context_event_sha256"]
        assert gui["selected_event_SHA256"]["actual_actor_wire_request"] == source_packet["actor_wire_event_sha256"]
        assert gui["selected_event_SHA256"]["actual_actor_wire_response"] == source_packet["actor_reply_event_sha256"]
        save(out / "receipt.json", {"time": time.time(), "passed": True, "CPU_adversarial_checks": len(checks),
            "runtime_manifest_sha256": manifest_sha, "runtime_modified": False,
            "actual_noaux_original_request_read_not_reexecuted": "0063", "original_candidate_ordinal": 35,
            "actual_noaux_cross_host_HTTP_and_unchanged_fullhistory_insertion_bound": True,
            "linked_existing_native_audit": native_pointer, "source_packet_sha256": sha(source_packet_path),
            "new_actual_native_calls_counted": 0, "new_model_GUI_scorer_paid_calls": 0,
            "operations": {"3090": str(operation3090), "4090": str(operation4090)},
            "enabled_auxiliary_GPU_cycle_only_synthetic_adversarial_checks": True,
            "actual_enabled_mixed_HTTP_GPU_Controller_pipeline_proven": False,
            "full_mixed_auditor_ready": False,
            "remaining": ["actual enabled auxiliary invocation and complete native/cache-release primitive",
                "bind actual GPU transition tensor files and counters to that invocation",
                "bind original reply, frozen contract packet and actual actor insertion",
                "primary native tensor/ID audit using mapped session after actual auxiliary calls",
                "whole-trajectory semantic labels, official outcomes and paired efficacy"],
            "semantic_correctness_or_defense_efficacy_established": False})
        save(out / "seal.json", {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        result = {"root": str(out), "receipt_sha256": sha(out / "receipt.json"), "seal_sha256": sha(out / "seal.json")}
        save(pointer, result)
        print(json.dumps(dict(result, passed=True, CPU_adversarial_checks=len(checks),
            actual_noaux_HTTP_and_fullhistory_insertion_bound=True, actual_enabled_pipeline_proven=False,
            new_model_GUI_calls=0), ensure_ascii=False))
    except BaseException as error:
        save(out / "failure.json", {"time": time.time(), "error_type": type(error).__name__,
            "error": str(error), "runtime_modified": False, "new_model_GUI_scorer_calls": 0})
        save(out / "seal.json", {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        raise


if __name__ == "__main__":
    main()
