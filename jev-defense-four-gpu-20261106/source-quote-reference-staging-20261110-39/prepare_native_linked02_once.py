"""Repair CPU witness construction, preserving the failed BPE-path observation."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(PREVIOUS))
from join_source_reviews import verify_seal
from orchestrate import save, sha


def main():
    assert not (HERE / 'native-linked02-preparation.json').exists()
    failure = json.loads((HERE / 'native-CPU-failed.json').read_bytes())
    root = Path(failure['root'])
    assert verify_seal(root) == failure['seal_sha256']
    assert sha(root / 'failure.json') == failure['receipt_sha256']
    diagnosis = json.loads((HERE / 'native-token-path-diagnostic.json').read_bytes())
    rows = diagnosis['value']['results']
    assert len(rows) == 6
    for label in ['new', 'old']:
        assert next(r for r in rows if r['label']==label and r['encoding']=='character_tokens')['accepted']
        for encoding in ['compact','spaced']:
            row = next(r for r in rows if r['label']==label and r['encoding']==encoding)
            assert not row['accepted'] and row['failure']['token_text'] in ['.\",\"','.\",']
    source = (root / 'native_grammar_check.py').read_text(encoding='utf8')
    before = "        ids = tokenizer.encode(text, add_special_tokens=False)"
    after = "        # A CPU representability witness, not the generated model path. The\n        # preserved old and new schemas both reject some delimiter-spanning BPE\n        # merges; use exact native character tokens without changing runtime.\n        ids = [token for char in text for token in tokenizer.encode(char, add_special_tokens=False)]"
    assert source.count(before)==1
    source = source.replace(before,after,1)
    before = "        CPU_grammar_and_tokenizer_only=True, no_model_weights_loaded=True, no_CUDA_context_initialized=True,"
    after = "        witness_native_token_encoding='per-character exact native tokenizer IDs; CPU only, not model replies',\n        ordinary_BPE_path_failure_exists_in_both_original_and_proposed_grammar=True,\n        unchanged_runtime_and_canonical_library=True,\n        CPU_grammar_and_tokenizer_only=True, no_model_weights_loaded=True, no_CUDA_context_initialized=True,"
    assert source.count(before)==1
    source = source.replace(before,after,1)
    path = HERE / 'native_grammar_check_linked02.py'
    with path.open('x',encoding='utf8',newline='\n')as stream:stream.write(source)
    launcher = (root / 'run_native_CPU_once.py').read_text(encoding='utf8')
    launcher = launcher.replace('native-CPU-submission.json','native-CPU-linked02-submission.json')
    launcher = launcher.replace('native-reference-CPU-', 'native-reference-CPU-linked02-')
    launcher = launcher.replace('native_grammar_check.py','native_grammar_check_linked02.py')
    launcher = launcher.replace('launch-native-quote-reference-CPU-only-once','launch-linked02-native-reference-witness-CPU-only-once')
    with (HERE/'run_native_CPU_linked02_once.py').open('x',encoding='utf8',newline='\n')as stream:stream.write(launcher)
    save(HERE/'native-linked02-preparation.json',dict(original_failure=failure, diagnostic=str(HERE/'native-token-path-diagnostic.json'),
        diagnostic_sha256=sha(HERE/'native-token-path-diagnostic.json'),
        change='CPU test witnesses use exact one-character native IDs instead of requiring a particular merged BPE encoding. Both original and proposed schemas exhibit the preserved BPE-path restriction.',
        no_model_runtime_parser_validator_or_generation_change=True, no_claim_of_arbitrary_token_path_compatibility=True,
        checker_sha256=sha(path), launcher_sha256=sha(HERE/'run_native_CPU_linked02_once.py'), new_model_GUI_scorer_calls=0))
    print(json.dumps(dict(prepared=True, first_attempt_failure_preserved=True, no_runtime_change=True)))


if __name__=='__main__':
    main()
