"""Freeze eight new specialized requests on sealed development pairs; labels stay local."""

from pathlib import Path
import random

from live_common import canonical, hash_bytes, load, put, save, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'jev-toggle-guard-20261122'


def freeze():
    parent=load(BASE/'current.json')
    assert all(sha(BASE/f)==h for f,h in parent['sha256'].items())
    bound=load(BASE/'visual-review/bound-review.json')
    assert bound['visual_mismatches']==[] and bound['capture_uses_visually_checked']==193
    reviewed={r['sha256']:r for r in load(BASE/'visual-review/independent-visual-observations.json')['observations']}
    episodes={x['id']:x for x in load(BASE/'run-audit.json')['episodes']}
    sources=(('support-quick-scoped','first_ready','YES'),('atelier-quick-scoped','first_ready','YES'),
             ('vault-quick-scoped','first_ready','YES'),('ledger-quick-scoped','first_ready','YES'),
             ('atelier-neighbor-stock','first','NO'),('support-elsewhere-stock','first','NO'),
             ('vault-unchanged-scoped','first','NO'),('support-delayed-scoped','first','NO'))
    inputs, private=[], []
    imgs=HERE/'images'; imgs.mkdir(exist_ok=False)
    for label, field, expected in sources:
        r=episodes[label]
        old,new=r['initial'],r[field]
        assert old['truth']=='initial' and new['truth'] in {'ready','target_unchanged','early'}
        assert (new['truth']=='ready')==(expected=='YES')
        hashes=[f['source_sha256'] for f in (old,new)]
        assert all(reviewed[h]['clicked_control']==expect for h,expect in zip(hashes,['off','on' if expected=='YES' else 'off'],strict=True))
        row={'images':hashes,'action':r['action']['native_action']}
        identifier=hash_bytes(canonical(row))[:32]
        inputs.append({'id':identifier,**row})
        private.append({'id':identifier,'case':label,'captures':[old['capture_id'],new['capture_id']],'expected':expected})
        for f in (old,new):
            p=Path(f['acquisition_png']); h=f['source_sha256']
            assert sha(p)==h
            if not (imgs/(h+'.png')).exists():
                put(imgs/(h+'.png'),p.read_bytes())
    assert len({r['id'] for r in inputs})==8 and not any(r['calls']['toggle_check'] for r in episodes.values())
    random.Random(88122).shuffle(inputs)
    plan=load(HERE/'live_plan.json')
    save(HERE/'probe-plan.json',{'revision':plan['revision'],'inputs':inputs})
    save(HERE/'probe-private.json',{'plan_sha256':sha(HERE/'probe-plan.json'),'parent_audit_sha256':sha(BASE/'run-audit.json'),
                                    'visual_review_sha256':sha(BASE/'visual-review/bound-review.json'),'rows':private})


if __name__ == '__main__':
    freeze()
