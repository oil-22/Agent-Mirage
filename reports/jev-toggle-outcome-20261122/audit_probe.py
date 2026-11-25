"""Verify eight actual development forwards before any held-out inference."""

from pathlib import Path
import argparse

from audit_panel import verify_flash
from audit_toggle import verify_seal
from live_common import load, save, sha

HERE=Path(__file__).resolve().parent


def audit(root):
    m, remote=verify_seal(root)
    t=load(root/'run'/'terminal.json')
    assert m['stage']=='probe' and remote['exit_status']==t['gui_actions']==t['primary_calls']==t['scoring_calls']==0
    assert t['status']=='completed_probe' and t['calls']==m['max_calls']==len(t['replies'])==8
    assert m['files']['toggle_prompt.py']==sha(HERE/'toggle_prompt.py')
    p=load(HERE/'probe-private.json')
    assert p['plan_sha256']==sha(root/'probe-plan.json') and 'probe-private.json' not in m['files']
    targets={x['id']:x for x in p['rows']}
    bounds=load(root/'run'/'gpu-lease.json')
    state=load(root/'run'/'flash'/'loaded.json')
    assert bounds['holder']['uid']==state['process']['uid']==1033
    assert bounds['holder']['cmdline'][-1]=='probe_outcome.py' and list(bounds['roles'])==['flash']
    assert bounds['roles']['flash']['physical']==[7] and len(bounds['locks'])==4
    assert not bounds['smi_before']['compute'] and not bounds['smi_after']['compute']
    assert state['BF16'] and state['native_sdpa'] and state['fast'] is False
    release=load(root/'run'/'gpu-release.json')
    assert len(release['locks'])==4 and state['process']['pid'] in release['closed_worker_pids']
    assert all(x['state']=='released_verified' for x in release['locks'])
    assert not any(x['pid']==state['process']['pid'] for x in release['snapshot']['compute'])
    assert set(targets)=={d.parent.name for d in (root/'run'/'flash').glob('*/start.json')}=={d.parent.name for d in (root/'run'/'flash').glob('*/result.json')}
    out=[]
    for request, receipt in zip(load(root/'probe-plan.json')['inputs'],t['replies'],strict=True):
        k=request['id']; d=root/'run'/'flash'/k
        result=load(d/'result.json')
        assert receipt=={'id':k,'result_sha256':sha(d/'result.json'),'choice':result['choice']}
        previous, current=[str(root/'images'/(h+'.png')) for h in request['images']]
        frames={'previous':{'candidate_png':previous,'candidate_sha':request['images'][0]},
                'current':{'candidate_png':current,'candidate_sha':request['images'][1],'presence':'YES','receipt':'YES',
                           'action_sequence':1,'truth':'ready' if targets[k]['expected']=='YES' else 'unsupported'}}
        event={'request_id':k,'kind':'toggle_check','capture_id':'current','images':request['images'],'wire_sha256':result['wire_sha256']}
        checked=verify_flash(root,{**event,'forward_sha256':result['forward_sha256'],'decision':result['choice'],
                'p_yes':result['probabilities']['YES'],'native_seconds':result['native_seconds_with_trace'],
                'roundtrip_seconds':result['native_seconds_with_trace']},event,frames,'previous',{'native_action':request['action']},state,bounds)
        out.append({'case':targets[k]['case'],'id':k,'expected':targets[k]['expected'],'observed':checked['decision'],
                    'p_yes':checked['p_yes'],'wire_sha256':checked['wire_sha256'],'forward_sha256':checked['forward_sha256']})
    passed=all(row['expected']==row['observed'] for row in out)
    return {'attempt':root.name,'local_seal_sha256':sha(root/'local-seal.json'),'prompt_sha256':sha(root/'toggle_prompt.py'),
            'private_label_seal_sha256':sha(HERE/'probe-private.json'),'preflight_qualified':passed,'verified_calls':len(out),
            'source_scope':'Development only; eight new exact specialized request bodies on already image-reviewed prior screenshots.',
            'results':out,'gpu_release_sha256':sha(root/'run'/'gpu-release.json')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('attempt',type=Path)
    v=audit(p.parse_args().attempt.resolve());save(HERE/'probe-audit.json',v)
    print(v['preflight_qualified'],[(r['case'],r['observed'],round(r['p_yes'],3)) for r in v['results']])
