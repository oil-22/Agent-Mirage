"""CPU-only construction against preserved lawful wire projections. No model calls."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from history_utterance_ledger import (SourceBoundHistoryJudge, build_ledger, canonical,
    digest, prepare_main_judge_system)

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
RELEASE=BASE/'policy-preparation/image-observer-policy/gui-release-04'
ACTUAL_RELEASE=BASE/'policy-preparation/image-observer-policy/gui-migration-three-linked02/release'
PROJECTION=BASE/'complete-review-three-01/judge-legal-projection-linked03'


def read(path):
    return json.loads(path.read_bytes())


def save(root,name,value):
    with(root/name).open('x',encoding='utf8')as file:
        json.dump(value,file,ensure_ascii=False,indent=2)


if __name__=='__main__':
    out=HERE/'cpu-source-preparation-01'
    out.mkdir(exist_ok=False)
    sources=['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py',
             'tests/test_history_report_probe.py']
    frozen_before={str(RELEASE/name):digest((RELEASE/name).read_bytes())for name in sources}
    actual_source={str(ACTUAL_RELEASE/name):digest((ACTUAL_RELEASE/name).read_bytes())for name in sources if(ACTUAL_RELEASE/name).is_file()}
    assert digest((ACTUAL_RELEASE/'defense/core.py').read_bytes())==digest((RELEASE/'defense/core.py').read_bytes())
    assert digest((ACTUAL_RELEASE/'defense/prompts.py').read_bytes())==digest((RELEASE/'defense/prompts.py').read_bytes())
    module_spec=importlib.util.spec_from_file_location('unchanged_primary_prompts',RELEASE/'defense/prompts.py')
    prompts=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(prompts)
    core=ast.parse((RELEASE/'defense/core.py').read_text(encoding='utf8'))
    old_function=next(node for node in core.body if isinstance(node,ast.FunctionDef)and node.name=='historical_report_records')
    namespace={};exec(compile(ast.Module(body=[old_function],type_ignores=[]),'<unchanged-source-function>','exec'),namespace)
    old_reports=namespace['historical_report_records']
    projected_sources=[]
    tests=[]
    for number,phase,prefix in[(69,'verify',prompts.VERIFY),(70,'history_report',prompts.HISTORY_REPORT)]:
        path=PROJECTION/'review/judges'/f'{number:03}.json'
        source=read(path);assert source['phase']==phase
        request=source['original_verifier_request']
        native=source['actual_native_payload']
        assert native['operation']=='judge'
        # This is the preserved legal review projection: image bytes were replaced
        # by hash references at export. Text and source indices are exact; the full
        # projected body hash is not a historical full-wire/input-token identity.
        assert native['view']['messages']==request['public']['messages']
        assert native['system']==request['system']
        assert native['candidate']==request['candidate']
        public=SimpleNamespace(**copy.deepcopy(request['public']))
        before=canonical(public.messages)
        ledger=build_ledger(public)
        old=old_reports(public)
        new=ledger['complete_actor_text_block_index']
        assert len(old)==len(new)
        assert [(r['message_index'],r['text'])for r in old]==[(r['message_index'],r['exact_text'])for r in new]
        assert all(row['original_message_canonical_sha256']==digest(canonical(public.messages[row['message_index']]))for row in new)
        assert canonical(public.messages)==before
        prepared=prepare_main_judge_system(request['system'],public,phase)
        calls=[];events=[]
        def original_fixture(system,view,candidate):
            calls.append({'system':system,'view':view,'candidate':candidate})
            return source['raw_response']
        adapter=SourceBoundHistoryJudge(original_fixture,verify_prefix=prompts.VERIFY,
            history_prefix=prompts.HISTORY_REPORT,emit=lambda *args:events.append(args))
        result=adapter(request['system'],public,request['candidate'])
        assert result==source['raw_response']and len(calls)==len(events)==1
        assert calls[0]['system']==prepared.system and calls[0]['view']is public
        assert calls[0]['candidate']==request['candidate']and canonical(public.messages)==before
        assert request['system'].startswith(prefix)
        save(out,f'primary-{phase}-ledger-preparation.json',prepared.ledger)
        record={'judge_number':number,'phase':phase,'projection_path':str(path),'projection_file_sha256':digest(path.read_bytes()),
            'historical_actual_wire_sha256':source['actual_wire_sha256'],
            'projection_is_not_original_full_wirebody':True,'all_original_actor_text_and_indices_exact':True,
            'all_original_string_actor_records_already_present_before_new_ledger':True,
            'original_report_message_indices':[row['message_index']for row in old],
            'record_text_sha256_by_original_message_index':{str(row['message_index']):row['text_utf8_sha256']for row in new},
            'new_ledger_sha256':prepared.ledger_sha256,'old_system_utf8_bytes':len(request['system'].encode()),
            'new_system_utf8_bytes':len(prepared.system.encode()),'added_system_utf8_bytes':prepared.added_utf8_bytes,
            'token_count_or_capacity_not_measured':True,'actual_generation_not_replayed':True,
            'recorded_response_only_fixture_returned_unchanged':True,'fixture_callback_calls':1,
            'new_model_GUI_or_scorer_calls':0}
        projected_sources.append(record)
        tests.append({'test':phase+'_preserved_full_text_source_and_single_callback_boundary','passed':True})
    frozen_after={str(RELEASE/name):digest((RELEASE/name).read_bytes())for name in sources}
    assert frozen_before==frozen_after
    summary={'status':'isolated_CPU_source_preparation_passed','source_comparisons':projected_sources,
        'additional_source_integration_checks':tests,'unchanged_original_release_sources':frozen_before,
        'actual_migration_release_sources':actual_source,'gui04_and_actual_migration_core_and_prompts_byte_identical':True,
        'new_model_GUI_health_scorer_calls':0,'new_history_ledger_deployed':False,
        'original_full_history_images_precision_output_and_call_budgets_modified':False,
        'original_validator_schema_native_parser_and_generation_modified':False,
        'whole_original_main_prompt_not_tokenized':True,'new_prompt_capacity_or_efficacy_not_established':True,
        'source_projection_only_ledger_samples_not_actual_runtime_request_receipts':True}
    save(out,'receipt.json',summary)
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    mapping={p.name:digest(p.read_bytes())for p in out.iterdir()if p.is_file()}
    save(out,'seal.json',mapping)
    print(json.dumps({'out':str(out),'receipt_sha256':digest((out/'receipt.json').read_bytes()),
        'seal_sha256':digest((out/'seal.json').read_bytes()),'source_comparisons':projected_sources},ensure_ascii=False))
