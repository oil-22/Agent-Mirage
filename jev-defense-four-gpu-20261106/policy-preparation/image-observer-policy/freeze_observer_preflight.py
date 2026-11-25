"""Seal one finite image-only native request per distinct full original image."""
import argparse,json
from pathlib import Path
from image_observer import *

BASE=Path(__file__).resolve().parent


def save(path,value):
    with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2)


def main(a):
    old=BASE.parent/'flash-preflight-frozen-02'
    for name,expected in json.loads((old/'seal.json').read_bytes()).items():
        assert digest((old/name).read_bytes())==expected,name
    sources=[]
    shas=['564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848',
          'c60034d3e995b28eb7a5b68fe1ab31589b6ebcfc474296d176844e2c1cebe41d',
          'c4b3344c0140948b69d89b18ffd9f7f3c7517d71415595458dc3a82eb4f89b78',
          '3e254f50cd08f5798f0651523985f1bcd21a06ea85b6e88476cece3591b5910c',
          'b2cd327e62d841f9a96e811d2ea720aeae52074301749d1811aa595cbb453453',
          'f010474ff8699d243ea1bf022f34a55f035f77693579d3f2a89a3adba56d99ab']
    for i,sha in enumerate(shas,1):
        sources.append({'case_id':f'original-{i:02}','path':str(old/'images'/(sha+'.png')),
            'image_sha256':sha,'source_receipt':str(old/'seal.json'),
            'source_receipt_sha256':digest((old/'seal.json').read_bytes()),
            'scope':'previously seen original screenshot; new generic joint observer native input, nonblind development'})
    extras=json.loads(a.extra_sources.read_bytes())
    sources+=extras['sources']
    assert 1<=len(sources)<=60
    assert len({r['case_id']for r in sources})==len(sources)
    # Pure footer, actual native no-results and original sparse/buttons-only must
    # be supplied and reviewed before this new semantic preflight can be sealed.
    assert {'normal_footer','readable_no_results','buttons_only_sparse'}<=set(extras['required_source_coverage'])
    a.root.mkdir(exist_ok=False);(a.root/'wire').mkdir();(a.root/'images').mkdir()
    (a.root/'observer-contract.json').write_bytes((BASE/'observer-contract.json').read_bytes())
    rows=[];admission=[];seen={}
    for source in sources:
        raw=Path(source['path']).read_bytes();sha=digest(raw)
        assert sha==source['image_sha256']
        p=Path(source['source_receipt']);assert digest(p.read_bytes())==source['source_receipt_sha256']
        if sha in seen:
            seen[sha]['additional_source_bindings'].append(source)
            continue
        class Image:pass
        image=Image();image.raw=raw
        observation_id='frozen-image-observer-'+source['case_id']
        body=ObserverClient.build_body(image,observation_id,
            request_id=digest(canonical([REVISION,source['case_id'],sha,digest(wire(contract()))]))[:32])
        exact=wire(body);fingerprint=digest(canonical({k:v for k,v in body.items()if k!='request_id'}))
        name='wire/'+source['case_id']+'.json';(a.root/name).write_bytes(exact)
        (a.root/'images'/(sha+'.png')).write_bytes(raw)
        row={'case_id':source['case_id'],'wire':name,'wire_sha256':digest(exact),
            'fingerprint_excluding_request_id':fingerprint,'image_sha256':sha,
            'source_binding':source,'additional_source_bindings':[],
            'native_question_order':list(QUESTIONS),
            'native_option_order':{k:list(q['criteria'])for k,q in QUESTIONS.items()}}
        rows.append(row);seen[sha]=row
        admission.append({'case_id':source['case_id'],'fingerprint':fingerprint,'wire_sha256':digest(exact)})
    cap=len(rows)
    plan={'policy':POLICY,'model':MODEL,'revision':REVISION,'requests':rows,
          'max_new_flash_calls':cap,'new_joint_questions_per_image':3,
          'total_original_image_sources':len(sources),'unique_native_image_inputs':cap,
          'observer_contract_sha256':digest((a.root/'observer-contract.json').read_bytes()),
          'semantic_scope':'selected previously known and fresh native-image development controls; not blinded or independent tasks',
          'no_task_target_history_candidate_or_injection_in_native_input':True,
          'screenshot_does_not_establish_freshness':True,
          'coverage':extras['required_source_coverage'],'positive_explicit_loading_source':False,
          'loading_coverage_caveat':'No genuine explicit positive loading source is available; blank is not a positive loading control.',
          'new_main_27B_GUI_scorer_paid_calls':0,'automatic_retries':False,
          'first_request_is_native_smoke_and_generic_control_not_extra_call':True,
          'old_19_task_specific_requests':'superseded_UNSENT'}
    save(a.root/'plan.json',plan)
    save(a.root/'server-admission.json',{'mode':'image_observer_preflight','max_new_calls':cap,
        'GUI_actions':0,'requests':admission})
    save(a.root/'source-receipt-bindings.json',{'sources':sources,'extra_source_receipt':str(a.extra_sources),
        'extra_source_receipt_sha256':digest(a.extra_sources.read_bytes())})
    save(a.root/'seal.json',{str(p.relative_to(a.root)).replace('\\','/'):digest(p.read_bytes())for p in a.root.rglob('*')if p.is_file()})
    print(json.dumps({'frozen':str(a.root),'max_new_flash_calls':cap,'contract_sha256':plan['observer_contract_sha256'],
                      'admission_sha256':digest((a.root/'server-admission.json').read_bytes()),'new_model_calls':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extra-sources',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    main(p.parse_args())
