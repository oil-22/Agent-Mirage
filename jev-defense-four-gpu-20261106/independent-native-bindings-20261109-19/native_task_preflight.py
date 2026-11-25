"""One finite native initialization/recapture admission; no agent/model/scoring."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from native_environment import NATIVE_ENV

HERE=Path(__file__).resolve().parent
RUNTIME=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def identity():
    p=Path('/proc',str(os.getpid()));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':os.getpid(),'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19]}


def main(root):
    assert os.getuid()==1015 and os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert not root.exists();root.mkdir();save(root/'process.json',identity())
    failure=None;rows=[];started=time.time();lease=None
    try:
        for name,expected in json.loads((HERE/'source-seal.json').read_bytes()).items():assert sha(HERE/name)==expected,name
        bindings=json.loads((HERE/'bindings-public.json').read_bytes())
        assert [row['task_id']for row in bindings['tasks']]==[0,3,17,58,89,94,114,125]
        os.environ.update(NATIVE_ENV)
        lease=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a')
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stat=os.fstat(lease.fileno())
        assert stat.st_uid==1015
        save(root/'site-lease.json',{'identity':identity(),'fd':lease.fileno(),'inode':stat.st_ino,'device':stat.st_dev,
             'path':str(Path(lease.name)),'fdinfo':Path('/proc',str(os.getpid()),'fdinfo',str(lease.fileno())).read_text(),
             'held_for_all_native_initializations_and_recaptures':True})
        ids=[row['id']for row in bindings['dedicated_site']]
        containers=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
        assert all(v['Id']==expected and v['Config']['Labels']['owner']=='whz-qwen27-vwa'and v['State']['Running']for v,expected in zip(containers,ids))
        assert sha(RUNTIME/'native/run_reddit_internvl_smoke.py')==bindings['native_source_SHA']
        assert sha(RUNTIME/'upstream/evaluation_harness/evaluators.py')==bindings['native_URL_scorer_source_SHA']
        sys.path[:0]=[str(RUNTIME/'native'),str(RUNTIME/'upstream')]
        from browser_env import ScriptBrowserEnv
        from browser_env.auto_login import renew_comb
        from evaluation_harness.evaluators import evaluator_router
        from run_reddit_internvl_smoke import png
        from PIL import Image
        auth=root/'.auth';auth.mkdir();auth.chmod(0o700)
        renew_comb(['classifieds'],str(auth))
        for source in bindings['tasks']:
            task=source['task_id'];target=root/('task-'+str(task));target.mkdir()
            save(target/'started.json',{'time':time.time(),'task_id':task,'new_model_agent_scorer_calls':0})
            original=Path(source['original_private_path']);assert sha(original)==source['original_private_SHA']
            raw=original.read_bytes();v=json.loads(raw)
            mapped=json.loads(raw.decode().replace('192.0.2.10:19980','192.0.2.10:29980'))
            assert mapped['require_reset']is False and mapped['eval']['eval_types']==['url_match']
            mapped['storage_state']=str(auth/'classifieds_state.json')
            config=target/'official-config.PRIVATE.json';save(config,mapped);config.chmod(0o600)
            # Native routing is loaded, never invoked against an initial-state score.
            router=evaluator_router(config)
            assert type(router).__name__=='EvaluatorComb'
            env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,
                 viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
            try:
                obs,info=env.reset(seed=20261011,options={'config_file':str(config)})
                first=png(obs);second=png(env._get_obs())
                with Image.open(io.BytesIO(first))as image:assert image.size==(1280,720)
                with Image.open(io.BytesIO(second))as image:assert image.size==(1280,720)
                (target/'initial.png').write_bytes(first);(target/'same-live-recapture.png').write_bytes(second)
                assert env.page.url.startswith('http://192.0.2.10:29980')
                row={'task_id':task,'status':'passed','original_config_SHA':sha(original),'mapped_private_config_SHA':sha(config),
                     'public_task_intent_SHA':hashlib.sha256(v['intent'].encode()).hexdigest(),
                     'source_start_url':source['start_url'],'actual_initial_url':env.page.url,
                     'initial_image_SHA':hashlib.sha256(first).hexdigest(),'same_live_recapture_SHA':hashlib.sha256(second).hexdigest(),
                     'same_live_native_env_recapture':True,'native_resolution':[1280,720],'seed':20261011,
                     'native_URL_scorer_router_loaded_not_invoked':True,'model_calls':0,'agent_actions':0,'official_scores':0,
                     'site_reset':False,'private_scorer_fields_never_model_input':True}
                save(target/'receipt.json',row);rows.append(row)
            finally:env.close()
            save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
        save(root/'receipt.json',{'time':time.time(),'status':'completed','tasks':rows,'task_count':len(rows),
             'bindings_public_SHA':sha(HERE/'bindings-public.json'),'source_seal_SHA':sha(HERE/'source-seal.json'),
             'model_GPU_agent_scorer_paid_calls':0,'initial_browser_navigations':8,'same_live_recaptures':8,
             'no_site_reset_or_fixture_import':True,'actual_trajectory_GUI_or_efficacy_established':False,
             'protocol_freeze_service_and_full_GUI_launch_still_pending':True})
    except BaseException:
        failure={'traceback':traceback.format_exc(),'completed_task_ids':[row['task_id']for row in rows],
                 'new_model_GPU_agent_scorer_calls':0,'automatic_retry':False}
        save(root/'failure.json',failure)
    finally:
        if lease is not None:lease.close()
        save(root/'terminal.json',{'time':time.time(),'started':started,'status':'failed'if failure else'completed',
                                  'completed_tasks':len(rows),'error':failure,'no_automatic_retry':True})
        save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
    return 1 if failure else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(parser.parse_args().output))
