"""Prepare a read-only auxiliary auditor from one immutable old native reply.

Uses CPU tokenization only, no model weights/inference, GUI, score or live API.
The completed control is read, never retried or counted as a new observation.
"""
import base64
import importlib.util
import json
from pathlib import Path
import time

from orchestrate import HERE, PACKAGE, remote, save, sha, COMMON
from auxiliary_receipt_checks import check_auxiliary_receipts
from check_auxiliary_receipt_audit import run_checks


def main():
    pointer = HERE / "auxiliary-receipt-audit-preparation-created.json"
    assert not pointer.exists()
    old = HERE.parent / "unicode-guard-real-preflight-20261109-18"
    collection = old / "terminal-collection-1794218465768999100"
    receipt = json.loads((collection / "receipt.json").read_bytes())
    relative = "worker/auxiliary/T03-filled-filter"
    expected = next(row for row in receipt["sealed_calls_verified"] if row["directory"] == relative)
    original = collection / "original" / relative
    assert sha(original / "seal.json") == expected["seal_sha256"]
    old_seal = json.loads((original / "seal.json").read_bytes())
    assert sha(original / "effective-generation.json") == old_seal["effective-generation.json"]
    expected_generation = json.loads((original / "effective-generation.json").read_bytes())
    ref = json.loads((PACKAGE / "auxiliary-identity-reference.json").read_bytes())
    for key in ["max_new_tokens", "do_sample", "temperature", "top_p", "top_k", "num_beams",
                "num_return_sequences", "eos_token_id"]:
        assert expected_generation[key] == ref["generation"][key]
    spec = importlib.util.spec_from_file_location("frozen_read_only_structural_schema", PACKAGE / "bounded_schema.py")
    schema_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema_module)
    helper = (HERE / "auxiliary_receipt_checks.py").read_text(encoding="utf8")
    out = HERE / ("auxiliary-receipt-audit-preparation-" + str(time.time_ns()))
    out.mkdir()
    for name in ["auxiliary_receipt_checks.py", "check_auxiliary_receipt_audit.py",
                 "prepare_auxiliary_receipt_audit.py"]:
        with (out / name).open("xb") as stream:
            stream.write((HERE / name).read_bytes())
    save(out / "expected-generation.json", expected_generation)
    expectation = {"model": ref["base_model"]["repo"], "revision": ref["base_model"]["revision"],
                   "prompt_sha256": sha(PACKAGE / "fixed-prompt.txt"),
                   "schema_sha256": schema_module.schema_sha256(),
                   "unicode_guard_sha256": sha(PACKAGE / "unicode_length_guard.py"),
                   "runtime_manifest_sha256": sha(PACKAGE / "manifest.json"),
                   "old_native_receipt_seal_sha256": expected["seal_sha256"],
                   "decision_adapter_loaded": False}
    save(out / "expectation.json", expectation)
    code = ("ROOT=" + repr(receipt["root"]) + "\nRELATIVE=" + repr(relative) +
            "\nEXPECTED_SEAL=" + repr(expected["seal_sha256"]) +
            "\nMODEL_REFERENCE=" + repr(ref) + "\nHELPER=" + repr(helper) + "\n" + COMMON + r'''
import base64
p=Path(ROOT)/RELATIVE
assert p.stat().st_uid==1033 and sha(p/'seal.json')==EXPECTED_SEAL
seal=json.loads((p/'seal.json').read_bytes())
verified={}
for name,expected_hash in seal.items():
 actual_hash=sha(p/name)
 assert actual_hash==expected_hash,name
 verified[name]=actual_hash
model_path=Path(MODEL_REFERENCE['base_model']['local_path'])
metadata=[]
for row in MODEL_REFERENCE['metadata_files']:
 assert sha(model_path/row['filename'])==row['sha256']
 metadata.append({'filename':row['filename'],'sha256':row['sha256']})
from transformers import AutoTokenizer
tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
actual=json.loads((p/'actual-generation.json').read_bytes())
text=tokenizer.decode(actual['output_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
ns={'__name__':'read_only_selected_native_ID_bytes'}
exec(compile(HELPER,'read-only-selected-native-ID-byte-audit','exec'),ns)
reconstructed=ns['selected_token_bytes'](tokenizer,actual['output_ids'],[248044,248046])
names=['request.json','prepared.json','first-forward.json','effective-generation.json','actual-generation.json',
 'sequence_ids.json','stateless-input-boundary.json','stateless-context-discarded.json',
 'actual-mask-steps.json','unicode-length-guard.json','raw-UTF8-validation.json']
data={name:json.loads((p/name).read_bytes())for name in names}
raw_files={name:base64.b64encode((p/name).read_bytes()).decode()for name in
 ['original.png','raw-output.txt','generated-raw-utf8.bin']}
import torch
assert not torch.cuda.is_initialized(),'Read-only tokenizer audit unexpectedly initialized CUDA'
print(json.dumps({'metadata':data,'raw_files_base64':raw_files,'verified_file_SHA256':verified,
 'independently_decoded_native_output':text,
 'independently_reconstructed_native_token_bytes_base64':base64.b64encode(reconstructed).decode(),
 'source':str(p),'source_seal_sha256':sha(p/'seal.json'),'files_verified':len(verified),
 'current_native_tokenizer_metadata_SHA_verified':metadata,'CUDA_initialized':False,
 'model_weights_loaded':False,'model_GUI_scorer_calls':0},ensure_ascii=False))
''')
    try:
        output, operation = remote("3090", code, "read-only-old-auxiliary-native-receipt-compatibility", timeout=55)
        value = json.loads(output)
        assert value["source_seal_sha256"] == expected["seal_sha256"]
        assert value["verified_file_SHA256"] == old_seal
        save(out / "original-artifact-bindings.json", value)
        data = value["metadata"]
        raw = {name: base64.b64decode(encoded) for name, encoded in value["raw_files_base64"].items()}
        arguments = dict(request=data["request.json"], original_image=raw["original.png"],
            fixed_prompt=(PACKAGE / "fixed-prompt.txt").read_text(encoding="utf8"),
            expected_model=expectation["model"], expected_revision=expectation["revision"],
            prepared=data["prepared.json"], first_forward=data["first-forward.json"],
            effective_generation=data["effective-generation.json"], expected_generation=expected_generation,
            actual_generation=data["actual-generation.json"], sequence_ids=data["sequence_ids.json"],
            raw_output=raw["raw-output.txt"], raw_native_token_bytes=raw["generated-raw-utf8.bin"],
            independently_decoded_native_output=value["independently_decoded_native_output"],
            independently_reconstructed_native_token_bytes=base64.b64decode(value["independently_reconstructed_native_token_bytes_base64"]),
            input_boundary=data["stateless-input-boundary.json"], discarded_context=data["stateless-context-discarded.json"],
            mask_steps=data["actual-mask-steps.json"], unicode_guard=data["unicode-length-guard.json"],
            utf8_validation=data["raw-UTF8-validation.json"],
            expected_schema_sha256=expectation["schema_sha256"],
            expected_unicode_guard_sha256=expectation["unicode_guard_sha256"],
            verified_file_SHA256=value["verified_file_SHA256"])
        baseline, checks = run_checks(arguments)
        save(out / "CPU-checks.json", {"passed": True, "checks": checks, "count": len(checks),
             "synthetic_mutations_not_new_visual_controls": True})
        save(out / "native-receipt-compatibility.json", baseline)
        save(out / "receipt.json", {"time": time.time(), "remote_operation": str(operation),
            "passed": True, "CPU_provenance_checks": len(checks), "old_native_reply_read_not_regenerated": True,
            "old_control": "T03-filled-filter", "old_control_added_to_result_count": False,
            "CUDA_initialized": False, "model_weights_loaded": False, "runtime_modified": False,
            "new_model_GUI_scorer_paid_calls": 0, "new32_actual_auxiliary_request_audited": False,
            "full_mixed_HTTP_GPU_transition_Controller_auditor_ready": False,
            "semantic_correctness_or_defense_efficacy_established": False})
        save(out / "seal.json", {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        save(pointer, {"root": str(out), "receipt_sha256": sha(out / "receipt.json"),
                       "seal_sha256": sha(out / "seal.json")})
        print(json.dumps({"root": str(out), "passed": True, "CPU_provenance_checks": len(checks),
                          "old_native_reply_read_not_regenerated": True, "new_model_GUI_calls": 0,
                          "full_mixed_auditor_ready": False}, ensure_ascii=False))
    except BaseException as error:
        save(out / "failure.json", {"time": time.time(), "error_type": type(error).__name__,
                                   "error": str(error), "no_runtime_change": True})
        raise


if __name__ == "__main__":
    main()
