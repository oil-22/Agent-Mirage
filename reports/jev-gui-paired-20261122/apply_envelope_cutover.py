"""One-time application of the authorized paired runtime change, after safe drain."""
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import control
from prepare import read, save, sha
from prepare_envelope_cutover import release, setup
from repair_handoff import REPAIR


def main():
    setup()
    root=control.ROOT
    target=root/'cutover-application.json'
    stop=REPAIR/'STOP-CUTOVER'
    assert read(root/'cpu-native-qualification.json')['result']['manifest_sha256']==control.POINTER['manifest_sha256']
    assert not (root/'model-submission.json').exists() and not (root/'gui-submission.json').exists()
    save(root/'cutover-worker-claim.json',{'pid':os.getpid(),'manifest_sha256':control.POINTER['manifest_sha256'],
                                         'start_time':time.time(),'only_apply_once':True})

    def log(phase, **extra):
        record={'time':time.time(),'phase':phase,**extra}
        with (root/'cutover-progress.jsonl').open('a',encoding='utf8')as f:
            f.write(json.dumps(record)+'\n');f.flush();os.fsync(f.fileno())
        print(json.dumps(record),flush=True)

    def alive_request():
        if stop.exists():
            raise RuntimeError('Local STOP-CUTOVER requested')

    try:
        deadline=time.monotonic()+6*60*60
        last=None
        with ThreadPoolExecutor(max_workers=2) as pool:
            while time.monotonic()<deadline:
                alive_request()
                f3090=pool.submit(release,'3090');f4090=pool.submit(release,'4090')
                model,gui=f3090.result(),f4090.result()
                if model['result']['released'] and gui['result']['released']:
                    break
                summary=[x['result'].get('pending','released')for x in (model,gui)]
                if summary!=last:
                    log('waiting_for_exact_pair_and_v1_seals',status=summary);last=summary
                time.sleep(20)
            else:raise TimeoutError('Original pair did not drain and preserve within this handoff window')
        expected=control.POINTER['old_prefix_if_drained_as_armed']
        assert model['result']['prefix']==gui['result']['prefix']==expected
        assert model['result']['terminals']==gui['result']['terminals']
        proof=root/'v1-release-cross-host-binding.json'
        save(proof,{'parent_original_prefix':expected,'both_host_terminal_sha256_equal':True,'model':model,'GUI':gui})
        log('parent_retired_with_both_terminal_receipts',parent_prefix=expected,proof_sha256=sha(proof))
        last=None
        while time.monotonic()<deadline:
            alive_request()
            slots=control.remote('3090',control.prefix('3090')+r'''
import json,sys
from pathlib import Path
p=Path(ROOT);sys.path.insert(0,str(p/'flash'))
from resource_guard import gpu_snapshot
s=gpu_snapshot();ready=len(s['gpu'])==8 and not s['compute']and all(v['free_mib']>=23000 for v in s['gpu'].values())
print(json.dumps({'eight_empty':ready,'cards':s['gpu'],'compute':s['compute']}))
''','linked-wait-empty-owned-card-set',timeout=45)
            free=slots['result']['eight_empty']
            if free:break
            if last!=free:log('waiting_for_eight_empty_GPUs',operation=slots['operation']);last=free
            time.sleep(30)
        else:raise TimeoutError('Eight empty cards unavailable after paired release')
        alive_request()
        service=control.submit()
        log('v2_single_service_submission',pid=service['pid'],attempts_before_GUI=0)
        deadline=time.monotonic()+15*60
        while time.monotonic()<deadline:
            alive_request()
            records=control.inspect('3090')['result']['records']
            if records.get('launcher-failure.json') or records.get('exit.json'):
                raise RuntimeError('Linked load failed or exited; preserve evidence, no retry')
            if all(records.get(k)for k in ('primary/ready.json','service/ready.json','primary/actual','service/actual')):
                break
            time.sleep(20)
        else:raise TimeoutError('Linked services did not become ready; no GUI and no rerun')
        alive_request()
        gui_launch=control.gui()
        log('v2_single_GUI_submission',pid=gui_launch['actual']['pid'],first_pair=gui_launch['first_pair'])
        deadline=time.monotonic()+8*60
        while time.monotonic()<deadline:
            alive_request()
            inspected=control.inspect('4090')
            r=inspected['result']['records'];status=r.get('batch/status.json') or {}
            if status.get('phase')in ('technical_failure','manually_stopped') or r.get('control/exit.json'):
                raise RuntimeError('Linked GUI failed or stopped during startup; no retry')
            if r.get('actual_site_lease')and status.get('phase')=='running':
                save(target,{'status':'linked_runner_active', 'manifest_sha256':control.POINTER['manifest_sha256'],
                            'parent_cross_host_proof_sha256':sha(proof), 'GUI_status_inspection':inspected,
                            'model_and_GUI_submission_seals':{n:sha(root/n)for n in ('model-submission.json','gui-submission.json')},
                            'new_planned_suffix':control.POINTER['planned_suffix'], 'completed_real_envelope_actions_asserted':False})
                log('v2_actual_GUI_running',run_id=status.get('run_id'),expected=status.get('expected'))
                return
            time.sleep(15)
        raise TimeoutError('Linked GUI did not produce a verified active state')
    except BaseException:
        save(target,{'status':'cutover_stopped_for_inspection', 'error':traceback.format_exc(),
                     'automatic_restart_attempted':False,'preserve_all_runs':True})
        raise


if __name__ == '__main__':
    main()
