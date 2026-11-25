"""Prepare mixed-session native audit with two immutable actual receipts.

Read-only CPU/tokenizer work only. No completed control is generated again.
"""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from orchestrate import COMMON, OUTPUT, REMOTE_PACKAGE, remote, save, sha


def verify(path):
    path = Path(path)
    for name, expected in json.loads((path / "seal.json").read_bytes()).items():
        assert sha(path / name) == expected, str(path / name)


def main():
    pointer = HERE / "primary-receipt-audit-preparation-created.json"
    assert not pointer.exists()
    package = HERE / "runtime-package"
    manifest = json.loads((package / "manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        assert sha(package / name) == expected, name
    native_pointer = json.loads((HERE / "new-replies-40-audit-created.json").read_bytes())
    native_path = Path(native_pointer["audit"])
    verify(native_path.parent)
    assert sha(native_path) == native_pointer["audit_sha256"]
    native = json.loads(native_path.read_bytes())
    assert native["passed"] and [row["request"] for row in native["requests"]] == ["0068", "0069"]
    expected = {}
    for authority in native["selected_binary_full_SHA_authorities"]:
        verify(authority["evidence"])
        old = json.loads((Path(authority["evidence"]) / "3090.json").read_bytes())
        row = next(item for item in old["sealed_requests"] if item["request"] == authority["request"])
        assert row["files_verified"] > 0 and row["seal_sha256"] == authority["request_seal_sha256"]
        expected[row["request"]] = row["seal_sha256"]
    sources = {name: (HERE / name).read_text(encoding="utf8") for name in
        ["auxiliary_receipt_checks.py", "mixed_exchange_checks.py", "mixed_journal_map.py",
         "primary_receipt_checks.py", "check_primary_receipt_audit.py"]}
    for name, source in sources.items():
        compile(source, name, "exec")
    out = HERE / ("primary-receipt-audit-preparation-" + str(time.time_ns()))
    out.mkdir()
    for name in sources:
        (out / name).write_bytes((HERE / name).read_bytes())
    (out / "prepare_primary_receipt_audit.py").write_bytes(Path(__file__).read_bytes())
    # Preserve the isolated source-query syntax failure and its linked repair;
    # neither parsed/loaded a model nor sent inference/GUI requests.
    query_roots = [HERE.parent / "full-history-gui-development-20261109-23/operations" / name for name in
        ["1794243319100730800-read-only-primary-receipt-source-binding-discovery",
         "1794243335517869200-read-only-primary-receipt-source-binding-linked02"]]
    provenance = []
    for folder in query_roots:
        provenance.append({"root": str(folder), "files_sha256": {p.name: sha(p) for p in folder.iterdir() if p.is_file()}})
    save(out / "source-query-failure-and-linked-repair.json", {
        "operations": provenance, "failure": "CPU source-query SyntaxError before imports or file reads",
        "repair": "Only separated the conditional else token; original failed source/logs retained",
        "new_model_GUI_scorer_calls": 0})
    try:
        code = ("ROOT=" + repr(OUTPUT) + "\nPACKAGE=" + repr(REMOTE_PACKAGE) +
            "\nEXPECTED=" + repr(expected) + "\nSOURCES=" + repr(sources) +
            "\nMANIFEST_SHA=" + repr(sha(package / "manifest.json")) + "\n" + COMMON + r'''
import copy,importlib.util,sys,types
r=Path(ROOT);package=Path(PACKAGE)
assert os.getuid()==1033 and sha(package/'manifest.json')==MANIFEST_SHA
manifest=json.loads((package/'manifest.json').read_bytes())
for name in ['model_runtime.py','prefill_residency.py','release/defense/qwen_backend.py',
 'release/defense/schema.py','release/defense/prompts.py','primary-reference.json','actor-template.json']:
 assert sha(package/name)==manifest['files'][name],name
for name in ['auxiliary_receipt_checks.py','mixed_exchange_checks.py','mixed_journal_map.py',
 'primary_receipt_checks.py','check_primary_receipt_audit.py']:
 module=types.ModuleType(name[:-3]);sys.modules[name[:-3]]=module
 exec(compile(SOURCES[name],name,'exec'),module.__dict__)
mapper=sys.modules['mixed_journal_map']
events,chain=mapper.verified_events((r/'worker/journal/events.jsonl').read_bytes())
plan=json.loads((package/'plan.json').read_bytes());carry=json.loads((package/'carryover/state.json').read_bytes())
mapping=mapper.map_requests(events,plan['queue'],carry['initial_transport_counts'])
reference=json.loads((package/'primary-reference.json').read_bytes());model=Path(reference['primary_model'])
runtime=json.loads(Path(reference['primary_expected_runtime']).read_bytes())
for name,expected_hash in runtime['metadata_sha256'].items():assert sha(model/name)==expected_hash,name
assert sha(package/'release/defense/qwen_backend.py')==reference['primary_backend_sha256']
from transformers import AutoTokenizer,GenerationConfig
tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=True)
metadata={name:sha(model/name)for name in ['tokenizer.json','tokenizer_config.json','special_tokens_map.json','chat_template.jinja','generation_config.json','config.json']if(model/name).is_file()}
expected_map={'model.visual':3,'model.language_model.embed_tokens':3,'model.language_model.norm':2,
 'model.language_model.rotary_emb':2,'lm_head':2}
for i in range(64):expected_map['model.language_model.layers.'+str(i)]=0 if i<18 else 1 if i<36 else 2 if i<51 else 3
assert expected_map==json.loads((r/'worker/new-placement.json').read_bytes())['device_map']
template=json.loads((package/'actor-template.json').read_bytes());actor_parameters={k:v for k,v in template.items()if k!='messages'}
schema=types.ModuleType('frozen_source_schema');exec(compile((package/'release/defense/schema.py').read_bytes(),'frozen-schema','exec'),schema.__dict__)
prompts=types.ModuleType('frozen_source_prompts');exec(compile((package/'release/defense/prompts.py').read_bytes(),'frozen-prompts','exec'),prompts.__dict__)
arguments={};bindings=[]
for ident,expected_seal in EXPECTED.items():
 p=r/'worker/requests'/ident;assert sha(p/'seal.json')==expected_seal
 seal=json.loads((p/'seal.json').read_bytes())
 names=['external-wire.json','response.json','prepared.json','first-forward.json','effective-generation.json',
  'actual-generation.json','native-call.json','sequence_ids.json','forward-count.json']
 data={}
 for name in names:
  assert sha(p/name)==seal[name],name
  data[name]=json.loads((p/name).read_bytes())
 wire=data['external-wire.json'];payload=wire['payload'];op=payload['operation']
 assert op in ['actor','judge'] and op not in arguments
 row=next(item for item in mapping['sealed_requests']if item['request']==ident)
 assert row['seal_sha256']==expected_seal
 run=next(item for item in plan['queue']if item['run_id']==row['trajectory_id'])
 assert run['observer_enabled']is False
 cfg=GenerationConfig.from_pretrained(model,local_files_only=True)
 cfg.do_sample=False;cfg.max_new_tokens=2048 if op=='actor' else 4096
 if op=='actor':cfg.temperature=0.0
 else:cfg.temperature=1.0;cfg.top_p=1.0;cfg.top_k=0
 grammar=None
 if op=='judge':
  v=payload['view'];view=types.SimpleNamespace(observation_id=v['observation_id'],images=v['images'],messages=v['messages'])
  phase='history_report'if payload['system'].startswith(prompts.HISTORY_REPORT)else None
  grammar=schema.judge_schema(view,payload['candidate'],phase=phase)
 pref=r/'worker'/('prefill-residency-%03d.json'%row['primary_prefill_session'])
 prefill=json.loads(pref.read_bytes());prefill_event=next(e for e in events if e['sha256']==row['prefill_completion_event_sha256'])
 actual=data['actual-generation.json'];decoded=tokenizer.decode(actual['output_ids'],skip_special_tokens=True)
 arguments[op]=dict(external_request=wire,response=data['response.json'],mapped_request=row,
  prepared=data['prepared.json'],first_forward=data['first-forward.json'],effective_generation=data['effective-generation.json'],
  expected_generation=cfg.to_dict(),native_call=data['native-call.json'],actual_generation=actual,
  sequence_ids=data['sequence_ids.json'],forward_count=data['forward-count.json'],
  independently_decoded_native_output=decoded,verified_file_SHA256=seal,prefill=prefill,
  prefill_completion_event=prefill_event,expected_device_map=expected_map,expected_group_order=list(expected_map),
  expected_actor_parameters=actor_parameters,expected_verifier_schema=grammar)
 bindings.append({'request':ident,'native_request_seal_sha256':expected_seal,
  'primary_prefill_session':row['primary_prefill_session'],'prefill_file':str(pref),'prefill_file_sha256':sha(pref),
  'prefill_completed_event_sha256':prefill_event['sha256'],'native_effective_generation_sha256':seal['effective-generation.json'],
  'source_rebuilt_effective_generation_sha256':hashlib.sha256(mapper.canonical(cfg.to_dict())).hexdigest(),
  'independently_decoded_text_sha256':hashlib.sha256(decoded.strip().encode()).hexdigest()})
result=sys.modules['check_primary_receipt_audit'].run_checks(arguments)
import torch
assert not torch.cuda.is_initialized()
for name,expected_hash in metadata.items():assert sha(model/name)==expected_hash
print(json.dumps({'result':result,'bindings':bindings,'worker_chain':chain,'native_tokenizer_current_metadata_sha256':metadata,
 'original_checkpoint_metadata_sha256':runtime['metadata_sha256'],'source_rebuilt_generation_from_original_model_config':True,
 'native_generation_backend_source_sha256':sha(package/'release/defense/qwen_backend.py'),
 'CUDA_initialized':False,'model_weights_loaded':False,'runtime_modified':False,'new_model_GUI_scorer_calls':0},ensure_ascii=False))
''')
        compile(code, "readonly-primary-native-receipt-audit-preparation", "exec")
        output, operation = remote("3090", code, "readonly-primary-native-receipt-and-mixed-session-preparation", timeout=55)
        value = json.loads(output)
        assert value["result"]["passed"]
        save(out / "source-bound-CPU-result.json", value)
        save(out / "receipt.json", {"time": time.time(), "passed": True,
            "CPU_adversarial_checks": value["result"]["count"], "remote_operation": str(operation),
            "runtime_manifest_sha256": sha(package / "manifest.json"),
            "actual_original_requests_read_not_regenerated": ["0068", "0069"],
            "existing_nonoverlapping_native_audit": native_pointer,
            "full_original_binary_SHA_authorities": native["selected_binary_full_SHA_authorities"],
            "complete_actor_and_verifier_contexts_source_rebuilt": True,
            "native_effective_generation_source_rebuilt_exact": True,
            "native_tokenizer_output_ID_decode_independent": True,
            "primary_only_prefill_session_and_detailed_moves_bound": True,
            "actual_auxiliary_or_cross_track_branch_executed": False,
            "synthetic_mixed_index_test_is_not_real_auxiliary_inference": True,
            "full_mixed_auditor_ready": False, "runtime_modified": False,
            "new_model_GUI_scorer_paid_calls": 0,
            "semantic_Mirage_or_defense_efficacy_established": False})
        save(out / "seal.json", {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        result = {"root": str(out), "receipt_sha256": sha(out / "receipt.json"), "seal_sha256": sha(out / "seal.json")}
        save(pointer, result)
        print(json.dumps(dict(result, passed=True, CPU_adversarial_checks=value["result"]["count"],
            original_requests_read_not_generated=["0068", "0069"], new_model_GUI_calls=0), ensure_ascii=False))
    except BaseException as error:
        save(out / "failure.json", {"time": time.time(), "type": type(error).__name__, "message": str(error),
            "runtime_modified": False, "new_model_GUI_calls": 0})
        save(out / "seal.json", {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        raise


if __name__ == "__main__":
    main()
