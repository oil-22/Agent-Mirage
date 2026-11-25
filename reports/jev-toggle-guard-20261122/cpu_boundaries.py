"""Exercise safety edges without initializing models or opening a browser."""

import base64
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from PIL import Image, ImageDraw

from gate_core import Frame
from live_common import canonical, save, sha
from toggle_protocol import DISPATCH, PROBE, QUESTION, eligible, gray, targeted_request
from toggle_policy import route
import toggle_prompt


def main():
    passed = []

    def check(name, value):
        assert value, name
        passed.append(name)

    key = Ed25519PrivateKey.generate()
    bind = {'session_id': 'fixture-A', 'environment_id': 'document-A', 'loader': 'loader-A',
            'target': 'tab-A', 'public_key': key.public_key().public_bytes_raw().hex(), 'viewport':[120,100]}
    id_fields = {p: bind[p] for p in ('session_id','environment_id','loader','target')}
    action = {'type':'click','x':500.0,'y':500.0}
    hit = {'kind':'toggle_button','node':14,'rect':[38,35,82,69]}
    pos = [60,50]

    def packet(data):
        body = {**id_fields, **data}
        return {'body':body,'signature':key.sign(canonical(body)).hex()}

    def png(*, switched=False, elsewhere=False):
        im = Image.new('RGB',(120,100),'white')
        d = ImageDraw.Draw(im)
        d.rectangle((38,35,81,68),fill='#187bbc')
        d.text((44,46),'On' if switched else 'Off',fill='white')
        if elsewhere:
            d.rectangle((1,1,10,10),fill='black')
        out=BytesIO(); im.save(out,format='PNG')
        return out.getvalue()

    def capture(id_, step, raw, before=hit, after=hit, **extra):
        h = Frame(raw,id_,1).sha256
        f = Frame(raw,id_,1,{'session_id':bind['session_id'],'environment_id':bind['environment_id'],
                             'image_sha256':h,'capture_id':id_,'action_sequence':step})
        return f,packet({'protocol':PROBE,'capture_id':id_,'image_sha256':h,'action_sequence':step,'pointer':pos,
                         'before':before,'after':after,**extra})

    dispatch=packet({'protocol':DISPATCH,'action_sequence':1,'action':action,'pointer':pos,'hit':hit})
    a, b, c = capture('before',0,png()),capture('new1',1,png(switched=True)),capture('new2',1,png(switched=True))

    def proof(frames=(a,b,c), d=dispatch, act=action):
        return eligible(bind,act,d,[r[0] for r in frames],[r[1] for r in frames])

    def no(x):
        return {'decision':'NO','p_yes':x}

    def yes(x=.55):
        return {'decision':'YES','p_yes':x}

    check('stock_holds_gray',route('stock',no(.48),no(.48),False)=='hold')
    check('original_yes_preserved',route('scoped',yes(),None,False)=='original_yes')
    check('global_comparator_only',route('global046',no(.46),None,False)=='comparator_046')
    check('numeric_lower_boundary_exact',gray(no(.46)) and not gray(no(.459999999)))
    check('upper_excluded_and_nonfinite',not gray(no(.5)) and not gray(no(float('nan'))))
    check('first_gray_waits_for_recapture',route('scoped',no(.48),None,False)=='hold')
    check('strong_no_is_not_previous_gray',route('scoped',no(.48),no(.42),False)=='hold')
    check('new_strong_no_remains_no',route('scoped',no(.44),no(.48),False)=='hold')
    check('two_gray_only_scope_precheck',route('scoped',no(.47),no(.49),False)=='evaluate_control_hit')
    check('one_extra_per_action',route('scoped',no(.47),no(.49),True)=='hold')
    check('real_control_case',proof()['eligible'] is True)
    check('unrelated_pixels_rejected',proof((a,capture('x1',1,png(elsewhere=True)),capture('x2',1,png(elsewhere=True))))['reason']=='clicked_region_unchanged')
    wrong={**hit,'node':15}
    check('different_control_node',proof((a,b,capture('new2',1,png(switched=True),wrong,wrong)))['reason']=='different_controls')
    check('role_not_verified',proof((a,b,capture('new2',1,png(switched=True),None,None)))['reason']=='not_a_visible_toggle')
    check('occlusion_during_capture',not proof((a,b,capture('new2',1,png(switched=True),hit,None)))['eligible'])
    check('same_capture_is_not_recapture',not proof((a,b,b))['eligible'])
    check('another_session',not proof((a,b,capture('new2',1,png(switched=True),session_id='fixture-B')))['eligible'])
    check('action_not_bound',not proof(act={**action,'x':501})['eligible'])
    tampered=deepcopy(c[1]); tampered['body']['image_sha256']=a[0].sha256
    check('signed_png_binding',not proof((a,b,(c[0],tampered)))['eligible'])
    check('zero_image',not proof((a,b,(Frame(None,'new2',1),c[1])))['eligible'])
    check('substituted_image',not proof((a,b,(Frame(a[0].png,c[0].capture_id,1,c[0].receipt),c[1])))['eligible'])
    moved={**hit,'rect':[38,35,100,69]}
    check('moving_control_not_comparable',proof((a,b,capture('new2',1,png(switched=True),moved,moved)))['reason']=='control_moved')
    req=targeted_request(a[0].png,action,c[0].png)
    check('unmodified_full_pngs',[base64.b64decode(x.split(',',1)[1]) for x in req['images']]==[a[0].png,c[0].png])
    check('stateless_fixed_contract',set(req)=={'state','images','questions'} and list(req['questions'])==[QUESTION]
          and req['state'].endswith(canonical(action).decode()) and 'fixture-A' not in str(req['questions']))
    check('isolated_flash_import_unchanged_contract',toggle_prompt.targeted_request(a[0].png,action,c[0].png)==req
          and toggle_prompt.QUESTION==QUESTION)
    code = ('toggle_protocol.py','toggle_policy.py','toggle_prompt.py','live_capture.py','capture_gui.py','live_models.py','live_run.py',
            'live_plan.json','fixture.html','analysis-plan.json')
    save(Path(__file__).with_name('cpu-boundaries-v3.json'),{'status':'passed','names':passed,'codes':{k:sha(Path(__file__).with_name(k)) for k in code},
                                                        'test_source_sha256':sha(__file__),'new_model_calls':0})
    print(len(passed),'CPU boundary checks passed.')


if __name__ == '__main__':
    main()
