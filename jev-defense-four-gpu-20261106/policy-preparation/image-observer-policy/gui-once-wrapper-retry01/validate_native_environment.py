"""One new real native import/parser/scorer-loader check, no model/GUI actions."""
import argparse,ast,hashlib,json,os,sys,time,traceback
from pathlib import Path
from native_environment import NATIVE_ENV,PARENT_PREFLIGHT_SOURCE_SHA256

BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
RUNTIME=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
TASK=Path('/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452/classifieds_112.PRIVATE.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)


def main(output):
    assert os.getuid()==1015
    output.mkdir(exist_ok=False)
    result={'time':time.time(),'model_calls':0,'task_actions':0,'scorer_calls':0,
        'browser_navigation_or_authentication_calls':0,'native_environment':NATIVE_ENV,
        'native_environment_source_sha256':sha(Path(__file__).parent/'native_environment.py'),
        'validator_source_sha256':sha(Path(__file__)),'parent_successful_transport_source_sha256':PARENT_PREFLIGHT_SOURCE_SHA256}
    try:
        old=BASE/'gui-preparation-01/evidence/same-live-environment/receipt.json'
        assert sha(old)=='537b6a092defaf445f5bb32504b15ec9ffa18317fc07c16b25a858400e3234d5'
        original=json.loads(old.read_bytes());assert original['preflight_source_sha256']==PARENT_PREFLIGHT_SOURCE_SHA256
        source=Path(__file__).parent/'successful_parent_environment_transport.py'
        assert sha(source)==PARENT_PREFLIGHT_SOURCE_SHA256
        tree=ast.parse(source.read_text());source_env=None
        for node in ast.walk(tree):
            if isinstance(node,ast.Call)and ast.unparse(node.func)=='os.environ.update':
                source_env={k.arg:ast.literal_eval(k.value)for k in node.keywords}
        assert source_env==NATIVE_ENV,'Not the complete exact successful native environment'
        os.environ.update(NATIVE_ENV);os.environ['PYTHONDONTWRITEBYTECODE']='1'
        sys.path[:0]=[str(RUNTIME/'native'),str(RUNTIME/'upstream')]
        # Full relevant native source-tree environment dependency inventory.
        inventory=[]
        paths=[RUNTIME/'native/run_reddit_internvl_smoke.py']
        for directory in ('browser_env','evaluation_harness'):
            paths+=sorted((RUNTIME/'upstream'/directory).rglob('*.py'))
        for path in paths:
            parsed=ast.parse(path.read_text());reads=[]
            for node in ast.walk(parsed):
                if isinstance(node,ast.Subscript)and isinstance(node.ctx,ast.Load)and ast.unparse(node.value)=='os.environ':
                    reads.append({'line':node.lineno,'access':'subscript','expression':ast.unparse(node.slice)})
                elif isinstance(node,ast.Call)and ast.unparse(node.func)in('os.getenv','os.environ.get'):
                    reads.append({'line':node.lineno,'access':ast.unparse(node.func),'arguments':[ast.unparse(v)for v in node.args]})
            inventory.append({'path':str(path),'sha256':sha(path),'environment_reads':reads})
        write(output/'native-env-dependency-inventory.json',inventory)
        from run_reddit_internvl_smoke import SYSTEM,parse,action,png
        from browser_env import ScriptBrowserEnv
        from browser_env.actions import create_stop_action,create_page_focus_action
        from browser_env.auto_login import renew_comb
        from evaluation_harness.evaluators import evaluator_router
        from playwright.sync_api import sync_playwright,Page
        result['imports_passed']=True
        cases=[{'type':'click','x':100,'y':200},{'type':'type','text':'CPU contract only'},
            {'type':'press','key':'Enter'},{'type':'scroll','direction':'up'},
            {'type':'scroll','direction':'down'},{'type':'back'},{'type':'wait'},
            {'type':'stop','answer':'Environment import contract only'}]
        for item in cases:assert parse('<action>'+json.dumps(item)+'</action>')==item and isinstance(action(item),dict)
        for item in [{'type':'click','x':0,'y':200},{'type':'scroll','direction':'left'},{'type':'unbound'}]:
            try:action(item)
            except(ValueError,KeyError):pass
            else:raise AssertionError('Native rejection boundary changed')
        try:parse('<action>{}</action><action>{}</action>')
        except ValueError:pass
        else:raise AssertionError('Native parser duplicate action boundary changed')
        result.update(native_parser_passed=True,native_parser_positive_cases=8,native_parser_negative_cases=4)
        # The original URL-only evaluator is constructed, never scored here.
        assert sha(TASK)=='b2dd3cef7cc6357376b95ef8c64ae4fcad839fd7f705e55afbdeb4a3d6a83603'
        private=json.loads(TASK.read_bytes());assert private['require_reset']is False and private['eval']['eval_types']==['url_match']
        scorer=evaluator_router(TASK);result.update(official_scorer_loader_passed=True,scorer_class=type(scorer).__name__)
        with sync_playwright()as pw:
            executable=Path(pw.chromium.executable_path)
            assert executable.is_file()and sha(executable)==original['browser_sha256']
        result.update(native_browser_binary_verified=True,browser_executable=str(executable),
            browser_sha256=sha(executable),complete_native_env_source_bound=True,
            unchanged_release04_runner_sha256=sha(BASE/'gui-preparation-01/release/run_image_observer_vwa_validation.py'),
            native_dependency_inventory_sha256=sha(output/'native-env-dependency-inventory.json'),
            reused_prior_actual_scorer_transport_receipt_sha256=sha(old),
            no_new_scorer_execution=True,status='passed')
    except BaseException:
        result.update(status='failed',error=traceback.format_exc())
    write(output/'receipt.json',result)
    write(output/'seal.json',{p.name:sha(p)for p in output.iterdir()if p.is_file()})
    print(json.dumps({'output':str(output),'status':result['status'],'receipt_sha256':sha(output/'receipt.json'),
        'model_calls':0,'task_actions':0,'scorer_calls':0}))
    if result['status']!='passed':raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
