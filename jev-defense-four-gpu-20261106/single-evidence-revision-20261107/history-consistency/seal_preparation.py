"""Finalize only this isolated preparation package, never its parent release."""
import json
import time
from pathlib import Path

from history_utterance_ledger import digest


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    receipts={}
    for name in ['cpu-source-preparation-01','cpu-compact-preparation-linked02']:
        path=root/name;manifest=json.loads((path/'seal.json').read_bytes())
        for relative,expected in manifest.items():assert digest((path/relative).read_bytes())==expected
        receipts[name]={'receipt_sha256':digest((path/'receipt.json').read_bytes()),
                        'seal_sha256':digest((path/'seal.json').read_bytes())}
    preferred=root/'cpu-compact-preparation-linked02'
    for name in ['history_utterance_ledger.py','compact_history_utterance_ledger.py',
                 'test_history_utterance_ledger.py','test_compact_history_ledger.py',
                 'audit_source_preparation.py','audit_compact_source_preparation.py']:
        assert(root/name).read_bytes()==(preferred/'source'/name).read_bytes()
    receipt={'status':'isolated_CPU_preparation_complete_not_deployed','created_time':time.time(),
        'recommended_adapter':'compact_history_utterance_ledger.CompactSourceBoundHistoryJudge',
        'full_raw_ledger_model_projection':'prototype_retained_not_recommended',
        'distinct_CPU_boundary_checks':{'original_exact_ledger':21,'compact_projection':8,'total':29},
        'checks_observed_in_actual_tool_runs_not_reexecuted_by_finalizer':True,
        'additional_preserved_legal_source_constructions':['verify069','history_report070'],
        'same_original_actor_records_in_both_source_requests':19,
        'known_source_compact_added_UTF8_bytes_each':8185,
        'not_native_token_count_or_GPU_capacity_proof':True,
        'receipts':receipts,
        'existing_original_history_index_acknowledged':True,
        'no_hardcoded_known_item_page_price_or_expected_label':True,
        'surface_cues_are_not_semantic_automatic_blockers':True,
        'past_actor_statement_is_not_visual_truth':True,
        'auxiliary_model_does_not_receive_history_context':True,
        'complete_original_history_images_actor_verdicts_and_native_generation_unchanged':True,
        'original_validator_schema_parser_action_and_recovery_budgets_unchanged':True,
        'only_primary_prompt_addition_prepared':True,
        'new_prompt_conditions_require_full_native_source_and_capacity_preflight':True,
        'new_model_GUI_GPU_health_scorer_calls':0,'live_configuration_modified':False,
        'launch_ready':False,'Mirage_reduction_or_success_claim':False}
    with(root/'preparation-receipt.json').open('x',encoding='utf8')as file:
        json.dump(receipt,file,ensure_ascii=False,indent=2)
    manifest={str(path.relative_to(root)):digest(path.read_bytes())for path in root.rglob('*')
              if path.is_file()and'__pycache__'not in path.parts}
    with(root/'package-seal.json').open('x',encoding='utf8')as file:json.dump(manifest,file,indent=2)
    print(json.dumps({'root':str(root),'files':len(manifest),
        'receipt_sha256':digest((root/'preparation-receipt.json').read_bytes()),
        'package_seal_sha256':digest((root/'package-seal.json').read_bytes())}))
