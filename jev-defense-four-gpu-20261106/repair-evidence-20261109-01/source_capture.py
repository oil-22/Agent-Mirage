"""NEW manual native source controls. No model, scorer, site reset, or task trial."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import traceback
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
BASE = Path('/data/researcher/jev-defense-validation-20261103')
RUNTIME = BASE/'runtime-stage-01'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf8')as f:
        json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    assert os.getuid()==1015
    root=HERE/'source-controls';root.mkdir(exist_ok=False)
    sys.path[:0]=[str(RUNTIME/'native'),str(RUNTIME/'upstream')]
    from native_environment import NATIVE_ENV
    os.environ.update(NATIVE_ENV)
    from browser_env import ScriptBrowserEnv
    from browser_env.auto_login import renew_comb
    from run_reddit_internvl_smoke import png
    import subprocess
    ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
    records=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
    assert all(v['Id']==i and v['State']['Running']and v['Config']['Labels']['owner']=='whz-qwen27-vwa'for v,i in zip(records,ids))
    auth=root/'.auth';auth.mkdir();renew_comb(['classifieds'],str(auth))
    source=BASE/'task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
    cfg=json.loads(source.read_text().replace('192.0.2.10:19980','192.0.2.10:29980'))
    assert cfg['require_reset']is False
    cfg['storage_state']=str(auth/'classifieds_state.json')
    config=root/'source-config.PRIVATE.json';save(config,cfg);config.chmod(0o600)
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    rows=[];operations=[];error=None
    def capture(name,kind='native_live_capture'):
        p=root/name;p.mkdir();raw=png(env._get_obs());(p/'original.png').write_bytes(raw)
        row={'id':name,'image_sha256':sha(p/'original.png'),'source_kind':kind,'actual_url':env.page.url,
             'captured_at':time.time(),'source_file':'original.png','manual_source_operations':list(operations),
             'no_model_scorer':True,'not_a_GUI_task_trial':True,'not_semantic_gold':True}
        save(p/'source.json',row);rows.append(row)
    try:
        env.reset(seed=20261011,options={'config_file':str(config)})
        for query,name in [('basketball','basketball-list'),('watch','watch-list'),('rock','rock-list'),('__mirage_scope_control_20261109_no_match__','native-no-results')]:
            url='http://192.0.2.10:29980/index.php?'+urlencode({'page':'search','sPattern':query})
            response=env.page.goto(url,wait_until='domcontentloaded',timeout=120000)
            env.page.wait_for_timeout(500)
            operations.append({'native_GET':url,'status':None if response is None else response.status})
            capture(name)
            if query=='basketball':
                env.page.evaluate('window.scrollTo(0,document.body.scrollHeight)');env.page.wait_for_timeout(300)
                operations.append({'manual_scroll':'bottom','no_agent_action':True});capture('basketball-footer')
        # Preserve native full screenshot. No image is masked, cropped, resized or synthesized.
    except BaseException:
        error=traceback.format_exc();(root/'failure.txt').write_text(error)
    finally:
        env.close()
        save(root/'receipt.json',{'time':time.time(),'images':rows,'error':error,'operations':operations,'models':0,'scorer':0,'formal_task_actions':0,'no_reset_import_mutation':True,'source_capture_script_sha256':sha(__file__)})
        save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in sorted(root.rglob('*'))if p.is_file()and'.auth'not in p.parts and'PRIVATE'not in p.name})
    print(json.dumps({'root':str(root),'images':len(rows),'error':error,'model_calls':0}))
    return 1 if error else 0

if __name__=='__main__':raise SystemExit(main())
