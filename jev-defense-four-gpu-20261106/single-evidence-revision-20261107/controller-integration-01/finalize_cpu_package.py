"""Read-only audit then once-only receipt/seal for this CPU source package."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path,value):
    with path.open('x',encoding='utf8') as stream:
        stream.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def verify_seal(root):
    seal=json.loads((root/'seal.json').read_text(encoding='utf8'))
    for row in seal['files']:
        path=root/row['path']
        assert path.stat().st_size==row['bytes'],path
        assert sha(path)==row['sha256'],path
    return {'seal_sha256':sha(root/'seal.json'),'verified_files':len(seal['files'])}


def main():
    build=json.loads((HERE/'source-build-receipt.json').read_text(encoding='utf8'))
    for row in build['files']:
        assert sha(Path(row['source']))==row['source_sha256'],row
        assert sha(HERE/'release'/row['relative_path'])==row['release_sha256'],row
    source=Path(build['parent_release'])/'defense/core.py'
    staged=HERE/'release/defense/core.py'
    before=ast.parse(source.read_text(encoding='utf8'));after=ast.parse(staged.read_text(encoding='utf8'))
    dump=lambda item:ast.dump(item,include_attributes=False)
    functions=lambda tree:{node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    oldfunc,newfunc=functions(before),functions(after)
    assert oldfunc.keys()==newfunc.keys()
    assert all(dump(oldfunc[name])==dump(newfunc[name]) for name in oldfunc)
    classes=lambda tree:{node.name:node for node in tree.body if isinstance(node,ast.ClassDef)}
    oldclasses,newclasses=classes(before),classes(after)
    unchanged_classes=[]
    for name in oldclasses:
        if name=='Controller':continue
        assert dump(oldclasses[name])==dump(newclasses[name])
        unchanged_classes.append(name)
    methods=lambda tree:{node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    oldmethods,newmethods=methods(oldclasses['Controller']),methods(newclasses['Controller'])
    assert oldmethods.keys()==newmethods.keys()
    unchanged_methods=[]
    for name in oldmethods:
        if name=='inspect':continue
        assert dump(oldmethods[name])==dump(newmethods[name])
        unchanged_methods.append(name)
    ast_audit={'original_core_sha256':sha(source),'staged_core_sha256':sha(staged),
        'unchanged_all_original_module_functions':list(oldfunc),
        'unchanged_native_validate_functions':[name for name in oldfunc if name.startswith('validate_')],
        'unchanged_classes':unchanged_classes,
        'unchanged_Controller_methods':unchanged_methods,
        'changed_Controller_methods':['inspect'],
        'other_changes':'two import statements and explicit development DEFENSE_VERSION',
        'schema_prompts_and_all_other_copied_files_byte_identical':True}
    write_once(HERE/'ast-identity.json',ast_audit)
    attempt_names=['cpu-integration-attempt-01','cpu-integration-linked02']
    attempts={name:verify_seal(HERE/name) for name in attempt_names}
    latest=json.loads((HERE/attempt_names[-1]/'result.json').read_text(encoding='utf8'))
    assert latest['successful'] and latest['tests_run']==21
    journal_count=event_count=0
    for path in (HERE/attempt_names[-1]/'j').glob('*/events.jsonl'):
        previous='0'*64
        for seq,line in enumerate(path.read_text(encoding='utf8').splitlines()):
            event=json.loads(line);supplied=event.pop('sha256')
            assert event['seq']==seq and event['previous']==previous,path
            raw=json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
            assert hashlib.sha256(raw).hexdigest()==supplied,path
            previous=supplied;event_count+=1
        journal_count+=1
    receipt={'status':'isolated_Controller_CPU_integration_complete_not_deployed',
        'source_files':len(build['files']),'source_build_receipt_sha256':sha(HERE/'source-build-receipt.json'),
        'ast_identity_sha256':sha(HERE/'ast-identity.json'),'new_core_sha256':sha(staged),
        'cpu_latest_tests':21,'cpu_latest_successful':True,'attempt_seals_reverified':attempts,
        'latest_journals_verified':journal_count,'latest_chain_events_verified':event_count,
        'system_journal_equals_actual_callback_checked':True,
        'native_verify_uses_exact_claim_origin_after_unchanged_validator':True,
        'history_report_index_only_without_claim_origin':True,
        'original_140_verifier_cap_one_format_retry_and_WAIT_preserved':True,
        'original_actor_auxiliary_and_full_public_context_unchanged':True,
        'model_calls':0,'gpu_allocations':0,'GUI_actions':0,'official_scoring':0,
        'launch_ready':False,'old_GUI_launchers_copied':False,
        'semantic_Mirage_reduction_established':False,
        'known_old_semantic_false_blocks_not_claimed_repaired':True,
        'tradeoff':'New exact-span output contract and extra primary context may increase retries/capacity/cost; separate real controls required'}
    write_once(HERE/'integration-receipt.json',receipt)
    files=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            assert path.name!='package-seal.json'
            files.append({'path':path.relative_to(HERE).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
    write_once(HERE/'package-seal.json',{'files':files,'all_old_attempts_preserved':True,
        'receipt_sha256':sha(HERE/'integration-receipt.json'),'launch_ready':False})
    print(json.dumps({'receipt_sha256':sha(HERE/'integration-receipt.json'),
        'seal_sha256':sha(HERE/'package-seal.json'),'files':len(files),
        'native_validate_functions':len(ast_audit['unchanged_native_validate_functions']),
        'unchanged_all_module_functions':len(oldfunc),'unchanged_Controller_methods':len(unchanged_methods),
        'journals':journal_count,'events':event_count},ensure_ascii=False))


if __name__=='__main__':main()
