"""New linked development sources; no old terminal, model, or GUI is executed."""
from pathlib import Path
import hashlib
import json
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PARENT = BASE / 'full-gui-single-evidence-20261108-01'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def main():
    assert sha(PARENT / 'terminal-status-review-20261109-01/receipt.json') == '73b3e904591ec586488c16c0b74e17e84a800ff15f8802092a0e3ad44183d611'
    assert not (HERE / 'runtime-package').exists()
    package = HERE / 'runtime-package'
    shutil.copytree(PARENT / 'runtime-package', package,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'private.token', 'manifest.json', 'plan.json'))
    for name in ['candidate_units.py', 'scoped_absence.py']:
        shutil.copy2(HERE / name, package / 'release' / name)
    core = package / 'release/defense/core.py'
    original = core.read_text(encoding='utf8')
    needle = "        for retry in range(self.limits.max_format_retries+1):"
    assert original.count(needle) == 1
    addition = """        if phase=='verify':
            from candidate_units import candidate_source_units, extraction_instructions
            units=candidate_source_units(candidate)
            self.log.append('actual_candidate_quote_units',units)
            system+='\\n'+extraction_instructions(units)
"""
    changed = original.replace(needle, addition + needle)
    # No output rewriting or validator modification. The exact original candidate is sent.
    changed = changed.replace("VERSION='", "VERSION='")
    core.write_text(changed, encoding='utf8', newline='\n')
    absence = package / 'release/appearance_absence_source.py'
    text = absence.read_text(encoding='utf8')
    start = text.index('def absence_clauses(')
    end = text.index('def check_appearance_absence(', start)
    text = text[:start] + """def absence_clauses(candidate,proposal):
 from scoped_absence import route_absence
 return [r['text'] for r in route_absence(candidate,proposal)['clauses'] if r['extra_absence_read_required']]

""" + text[end:]
    text = text.replace(" historical=any(HISTORY.search(s)for s in clauses)", """ from scoped_absence import route_absence
 routing=route_absence(candidate,proposal)
 controller.log.append('scoped_absence_routing',routing)
 historical=any(r['historical_scope']for r in routing['clauses']if r['extra_absence_read_required'])""")
    text = text.replace('This instruction supplies no GUI fact or preferred action/status;',
        'A report that no figure is CLEARLY readable is bounded visual uncertainty, not proof that no person exists. A numeric count of visible items does not itself assert uniqueness of matching items or historical coverage. Check any separate categorical clause normally.\nThis instruction supplies no GUI fact or preferred action/status;')
    absence.write_text(text, encoding='utf8', newline='\n')
    # The strict v2 compact schema and its 6/6/2 limits remain unchanged.
    # Only the fixed generic request wording changes; no task-specific hints.
    contract = package / 'release/image_evidence.py'
    text = contract.read_text(encoding='utf8')
    start = text.index('FIXED_PROMPT = ')
    end = text.index('\n\nACTOR_BOUNDARY', start)
    fixed = (HERE / 'neutral_prompt.txt').read_text(encoding='utf8').strip()
    text = text[:start] + 'FIXED_PROMPT = ' + repr(fixed) + text[end:]
    text = text.replace("single-image-neutral-evidence-v3-compact-development", "single-image-neutral-evidence-v4-compact-quote-development")
    contract.write_text(text, encoding='utf8', newline='\n')
    # Clone only proven loading/audit logic. Finite control worker is a new entry point.
    for name in ['model_runtime.py', 'resource_gate.py', 'preflight_support.py', 'aux_identity_support.py',
                 'four_gpu_contract.py', 'primary-reference.json', 'auxiliary-identity-reference.json']:
        assert sha(package / name) == sha(PARENT / 'runtime-package' / name)
    save(HERE / 'parent-and-changes.json', {
        'time': time.time(), 'authorization': 'User: 做实验做到防御有效果为止',
        'parent': str(PARENT), 'parent_review_receipt_sha256': sha(PARENT / 'terminal-status-review-20261109-01/receipt.json'),
        'parent_manifest_sha256': sha(PARENT / 'runtime-package/manifest.json'),
        'parent_terminal_not_modified': True,
        'changes': ['verifier receives deterministic actual-candidate quote spans; exact origin validator unchanged',
                    'bounded visibility uncertainty avoids only the extra categorical-absence branch; original main checks retained',
                    'numeric local item count does not select full-history absence mode',
                    'single-image fixed prompt requests a smaller 4-text/4-element/1-uncertainty reading inside the unchanged 6/6/2 strict schema'],
        'tradeoffs': ['quote spans constrain attribution, not semantic truth or extraction completeness',
                      'lexical scope routing is conservative and cannot establish tiny-card clothing',
                      'smaller desired auxiliary inventory can omit relevant evidence; omissions never prove absence',
                      'known-task development sources, no general efficacy evidence'],
        'unchanged': ['full original main history and images', 'original actions/parser/strict validators', 'BF16/SDPA',
                      '2048 actor and auxiliary / 4096 verifier', '1 format retry', 'no semantic resampling'],
        'model_GUI_scorer_paid_calls': 0,
        'original_validator_sha256': sha(package / 'release/defense/schema.py'),
        'original_origin_validator_sha256': sha(package / 'release/claim_origin.py')})
    print(json.dumps({'new_linked_sources': str(package), 'model_GUI_calls': 0}))

if __name__ == '__main__':
    main()
