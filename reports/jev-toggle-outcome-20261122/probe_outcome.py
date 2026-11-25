"""One development pass with the fixed specialized question, identical Flash forward path."""

import base64
import os
from pathlib import Path
import traceback

from live_common import Child, load, save, sha, verify_input
from live_lease import Cohort

ROOT = Path(__file__).resolve().parent


def run():
    assert os.getuid() == 1033 and os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    m = verify_input(ROOT)
    assert m['stage'] == 'probe' and m['mode'] == 'live' and m['max_calls'] == 8
    plan, probe, config = (load(ROOT / n) for n in ('live_plan.json', 'probe-plan.json', 'service-config.json'))
    assert probe['revision'] == config['revision'] == plan['revision'] and len(probe['inputs']) == 8
    out = ROOT / 'run'; out.mkdir()
    errors, replies, calls = [], [], 0
    cohort = flash = None
    code = None
    def image(raw):
        return 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
    try:
        cohort = Cohort(plan, out, flash_only=True)
        flash = Child([config['python'], '-B', '-u', str(ROOT / 'live_models.py'), 'flash'],
                      out / 'flash-stderr.log', **cohort.worker('flash'))
        state = flash.call('ready', timeout=180)
        assert state['process']['pid'] == flash.p.pid and state['process']['uid'] == 1033 and state['BF16']
        for row in probe['inputs']:
            first, second = [ROOT/'images'/(h+'.png') for h in row['images']]
            assert [sha(p) for p in (first,second)] == row['images']
            body = {'previous':image(first.read_bytes()),'action':row['action'],'current':image(second.read_bytes())}
            calls += 1
            answer = flash.call('infer', {'request_id':row['id'],'body':body,'kind':'toggle_check'}, timeout=60)
            assert answer['ordered_images']==row['images'] and answer['request_id']==row['id']
            replies.append({'id': row['id'], 'result_sha256': sha(out/'flash'/row['id']/'result.json'), 'choice':answer['choice']})
            print(calls, '/', len(probe['inputs']), answer['choice'], flush=True)
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        if flash:
            try:
                code = flash.close()
                if code != 0:
                    errors.append(f'Flash exit: {code}')
            except Exception:
                errors.append(traceback.format_exc())
        if cohort:
            try:
                cohort.close({flash.p.pid} if flash else set())
            except Exception:
                errors.append(traceback.format_exc())
        save(out/'terminal.json', {'status':'technical_failure' if errors else 'completed_probe',
                                  'error':'\n'.join(errors) or None, 'calls':calls,'replies':replies,'worker_exit':code,
                                  'max_calls':8,'gui_actions':0,'primary_calls':0,'scoring_calls':0})
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(run())
