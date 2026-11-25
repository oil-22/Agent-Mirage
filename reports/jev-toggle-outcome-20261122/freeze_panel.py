"""Freeze the independent 18-pair held-out panel; no model or browser execution."""

from pathlib import Path
import random

from live_common import load, save, sha

HERE=Path(__file__).resolve().parent
PAIRS={'forge':('quick','delayed','refusal','neighbor','elsewhere'),
       'meadow':('quick','delayed','refusal','elsewhere','ordinary'),
       'harbor':('quick','delayed','neighbor','unchanged'),
       'vista':('quick','delayed','ordinary','unchanged')}
PREFLIGHT=('forge-quick-repair','meadow-quick-repair','harbor-delayed-repair','vista-quick-repair',
           'forge-refusal-repair','meadow-refusal-repair','forge-neighbor-repair','forge-elsewhere-repair',
           'harbor-neighbor-repair','harbor-unchanged-repair','vista-ordinary-repair')


if __name__=='__main__':
    cases=[]
    for j,(family,kinds) in enumerate(PAIRS.items()):
        for scenario in kinds:
            group=f'{family}-{scenario}'
            for arm in ('stock','repair'):
                cases.append({'id':f'{group}-{arm}','group':group,'family':family,'scenario':scenario,'arm':arm,
                              'action':'toggle','flow':'toggle','temporal':True,'delay_ms':(2900+j*420 if scenario=='delayed' else 0),
                              'task':'Use the preselected control once and report the result visible on the current screen.'})
    assert len({x['id'] for x in cases})==len(cases)==36
    random.Random(2026112202).shuffle(cases)
    template=load(HERE/'live_plan.json')
    settings={key:template[key] for key in ('revision','viewport','observation_seconds','recapture_seconds','fast_control_wait_seconds',
        'primary_max_output','primary_physical_gpus','flash_physical_gpu','max_primary_calls')}
    # The launch package maps this distinct holdout to live_plan.json. The
    # development attempt already sealed its copy of the earlier plan.
    save(HERE/'heldout-plan.json',{**settings,'max_distinct_target_questions':2,'preflight_ids':list(PREFLIGHT),
                                  'cases_by_arm':{'stock':18,'repair':18},'cases':cases,
                                  'scope':'Two arms, each with 12 normal cases (4 quick, 4 delayed, 2 explicit refusals, 2 ordinary) and 6 negative cases.'})
    print('Frozen',len(cases),'held-out episodes',sha(HERE/'heldout-plan.json'))
