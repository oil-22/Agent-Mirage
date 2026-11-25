"""Stage only an outcome-classification change; frozen32 never edited."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,sort_keys=True);stream.write('\n')


def main():
    pointer=HERE/'terminal-classification-preparation-created.json'
    assert not pointer.exists(),'Do not repeat completed preparation'
    root=HERE/('terminal-classification-preparation-'+str(time.time_ns()));root.mkdir()
    package=HERE/'runtime-package'
    assert sha(package/'manifest.json')=='c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    manifest=json.loads((package/'manifest.json').read_bytes())
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    original=(package/'run_independent_gui.py').read_text(encoding='utf8')
    core=(package/'release/defense/core.py').read_text(encoding='utf8')
    (root/'original-run_independent_gui.py').write_bytes((package/'run_independent_gui.py').read_bytes())
    (root/'original-core.py').write_bytes((package/'release/defense/core.py').read_bytes())
    old="   result['technical_status']='verifier_failure'if outcome=='blocked'and 'verifier_error:'in result_reason else'scoring_failure'if scoring=='failed'else'no_reported_infrastructure_failure'"
    assert original.count(old)==1
    replacement=("   from terminal_outcome_classification import classify_run_termination\n"
        "   result.update(classify_run_termination(outcome,result_reason,scoring,controller.verifier_calls,controller.limits.max_verifier_calls))")
    staged=original.replace(old,replacement)
    compile(staged,'isolated-runner-terminal-classification','exec')
    assert staged.replace(replacement,old)==original
    # Remove precisely the replacement nodes, restore the original single
    # assignment, then compare all remaining code's AST (including native GUI,
    # images/history/prompts/actions/scorer/Controller/cleanup) with the original.
    stage_tree=ast.parse(staged);original_node=ast.parse(old.lstrip()).body[0]
    changed=0
    for node in ast.walk(stage_tree):
        for field,value in ast.iter_fields(node):
            if not isinstance(value,list):continue
            for index,child in enumerate(value):
                if isinstance(child,ast.ImportFrom)and child.module=='terminal_outcome_classification':
                    assert isinstance(value[index+1],ast.Expr)
                    value[index:index+2]=[original_node];changed+=1;break
    assert changed==1 and ast.dump(stage_tree,include_attributes=False)==ast.dump(ast.parse(original),include_attributes=False)
    assert "if self.verifier_calls>=self.limits.max_verifier_calls:raise BudgetExhausted('verifier_call_cap')" in core
    source_bound=[]
    for line in core.splitlines():
        if 'except' in line and 'BudgetExhausted' in line and "return blocked('" in line:
            source_bound.append(line.strip())
    assert len(source_bound)==10
    (root/'staged-run_independent_gui.py').write_text(staged,encoding='utf8')
    sources={}
    for name in ['terminal_outcome_classification.py','check_terminal_outcome_classification.py','prepare_terminal_classification_once.py']:
        raw=(HERE/name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest();(root/name).write_bytes(raw)
    result=subprocess.run([sys.executable,'-B',str(HERE/'check_terminal_outcome_classification.py')],cwd=HERE,capture_output=True)
    (root/'checks.stdout.txt').write_bytes(result.stdout);(root/'checks.stderr.txt').write_bytes(result.stderr)
    for name,expected in sources.items():assert sha(HERE/name)==expected
    for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
    save(root/'receipt.json',dict(time=time.time(),passed=result.returncode==0,synthetic_CPU_checks=12,
        test_process_exit_code=result.returncode,sources=sources,source_bound_local_budget_exception_and_catches=source_bound,
        exact_only_outcome_classification_change_AST_verified=True,frozen_runtime_modified=False,deployed=False,
        actual_budget_terminal_not_yet_replayed=True,
        no_original_actor_judge_auxiliary_inputs_budgets_actions_or_scoring_changed=True,
        blocked_candidate_not_executed_and_no_extra_recovery_or_calls_granted=True,
        fresh_negative_WAIT_model_or_GUI_controls_not_claimed=True,new_model_GUI_scorer_paid_calls=0,
        no_efficacy_or_goal_completion_established=True))
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    record=dict(root=str(root),passed=result.returncode==0,receipt_sha256=sha(root/'receipt.json'),seal_sha256=sha(root/'seal.json'))
    save(HERE/(('terminal-classification-preparation-created'if result.returncode==0 else
        'terminal-classification-preparation-failed-'+root.name.split('-')[-1])+'.json'),record)
    print(json.dumps(record))
    if result.returncode:
        print(result.stderr.decode('utf8',errors='replace'));raise SystemExit(result.returncode)


if __name__=='__main__':main()
