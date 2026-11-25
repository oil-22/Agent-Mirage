"""Linked CPU preparation: preferred compact primary projection, original sources fixed."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from compact_history_utterance_ledger import (CompactSourceBoundHistoryJudge,
    prepare_compact_main_judge_system)
from history_utterance_ledger import canonical,digest
from audit_source_preparation import BASE,HERE,RELEASE,ACTUAL_RELEASE,PROJECTION


def read(path):return json.loads(path.read_bytes())


if __name__=='__main__':
    out=HERE/'cpu-compact-preparation-linked02';out.mkdir(exist_ok=False)
    save=lambda name,value:(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    old=HERE/'cpu-source-preparation-01'
    old_seal=read(old/'seal.json')
    for name,key in old_seal.items():assert digest((old/name).read_bytes())==key
    spec=importlib.util.spec_from_file_location('fixed_prompts',RELEASE/'defense/prompts.py')
    prompts=importlib.util.module_from_spec(spec);spec.loader.exec_module(prompts)
    original_files=['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py']
    original_sources={name:digest((RELEASE/name).read_bytes())for name in original_files}
    for name,key in original_sources.items():assert digest((ACTUAL_RELEASE/name).read_bytes())==key
    comparisons=[]
    for number,phase in[(69,'verify'),(70,'history_report')]:
        path=PROJECTION/'review/judges'/f'{number:03}.json';source=read(path)
        request=source['original_verifier_request'];view=SimpleNamespace(**copy.deepcopy(request['public']))
        before=canonical(view.messages);prepared=prepare_compact_main_judge_system(request['system'],view,phase)
        full=read(old/f'primary-{phase}-ledger-preparation.json')
        assert prepared.full_audit_ledger==full
        assert canonical(view.messages)==before
        records=prepared.compact_model_index['records'];assert len(records)==19
        for row,old_row in zip(records,full['complete_actor_text_block_index']):
            assert row['message_index']==old_row['message_index']and row['text_utf8_sha256']==old_row['text_utf8_sha256']
            assert row['text_character_span']==[0,len(old_row['exact_text'])]
        calls=[];events=[]
        def fixture(system,v,candidate):calls.append((system,v,candidate));return source['raw_response']
        adapter=CompactSourceBoundHistoryJudge(fixture,verify_prefix=prompts.VERIFY,
            history_prefix=prompts.HISTORY_REPORT,emit=lambda *args:events.append(args))
        assert adapter(request['system'],view,request['candidate'])==source['raw_response']
        assert len(calls)==len(events)==1 and calls[0][1]is view and calls[0][0]==prepared.system
        assert calls[0][2]==request['candidate']and canonical(view.messages)==before
        save(f'{phase}-compact-model-source-index.json',prepared.compact_model_index)
        record={'phase':phase,'source_projection_file':str(path),'source_projection_sha256':digest(path.read_bytes()),
            'historical_actual_wire_sha256':source['actual_wire_sha256'],
            'new_CPU_example_is_not_an_actual_runtime_request':True,
            'full_audit_ledger_unchanged_from_first_preparation':True,'complete_original_actor_text_and_indices_preserved':True,
            'compact_index_all19_sources_preserved':True,'original_main_system_utf8_bytes':len(request['system'].encode()),
            'first_full_ledger_added_utf8_bytes':next(r['added_system_utf8_bytes']for r in read(old/'receipt.json')['source_comparisons']if r['phase']==phase),
            'compact_added_utf8_bytes':prepared.added_utf8_bytes,
            'new_main_system_utf8_bytes':len(prepared.system.encode()),'compact_index_sha256':prepared.compact_index_sha256,
            'full_audit_ledger_sha256':prepared.full_ledger_sha256,'base_callback_calls':1,
            'unchanged_original_raw_response_returned_by_fixture':True,'new_model_calls':0}
        comparisons.append(record)
    for name,key in original_sources.items():assert digest((RELEASE/name).read_bytes())==key
    source_names=['history_utterance_ledger.py','compact_history_utterance_ledger.py',
                  'test_history_utterance_ledger.py','test_compact_history_ledger.py',
                  'audit_source_preparation.py','audit_compact_source_preparation.py']
    snapshot=out/'source';snapshot.mkdir()
    for name in source_names:(snapshot/name).write_bytes((HERE/name).read_bytes())
    receipt={'status':'preferred_compact_CPU_source_preparation_passed','comparisons':comparisons,
        'original_release_SHA':original_sources,'actual_migration_bytes_equal_to_gui04':True,
        'original_full_ledger_attempt_preserved':{'receipt_sha256':digest((old/'receipt.json').read_bytes()),
            'seal_sha256':digest((old/'seal.json').read_bytes()),'model_projection_status':'not_recommended_due_to_duplicate_metadata_size'},
        'separate_observed_test_runs':[
            {'suite':'test_history_utterance_ledger.py','distinct_tests':21,'observed_exit_code':0},
            {'suite':'test_compact_history_ledger.py','distinct_tests':8,'observed_exit_code':0}],
        'these_CPU_tests_are_not_semantic_accuracy_or_model_control_passes':True,
        'original_messages_images_candidate_parser_validator_schema_generation_unchanged':True,
        'system_addition_is_new_experimental_prompt_condition':True,'main_native_tokens_and_real_capacity_not_tested':True,
        'auxiliary_only_image_contract_unchanged':True,'new_model_GUI_health_scorer_or_GPU_calls':0,
        'live_configuration_or_launchers_modified':False,'live_deployment_ready':False,
        'not_a_proven_fix_for_historical_Mirage':True}
    save('receipt.json',receipt)
    manifest={str(p.relative_to(out)):digest(p.read_bytes())for p in out.rglob('*')if p.is_file()}
    save('seal.json',manifest)
    print(json.dumps({'out':str(out),'receipt_sha256':digest((out/'receipt.json').read_bytes()),
        'seal_sha256':digest((out/'seal.json').read_bytes()),'comparisons':comparisons},ensure_ascii=False))
