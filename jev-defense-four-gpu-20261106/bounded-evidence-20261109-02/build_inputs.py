"""Freeze new source-first controls; private review never enters inference."""
from pathlib import Path
import base64
import json
import sys
from ops import HERE, BASE, save, sha

sys.path.insert(0, str(HERE/'runtime-package/release'))
import image_evidence as contract

def main():
    names=['lamp-list','lamp-footer','bicycle-list','guitar-list','desk-list','native-no-results']
    # Single reviewer viewed the actual originals before any stage02 predictions.
    facts=[
        {'readable':'lamp results, 1 - 12 of 907 listings; Standing Lamp 10.00 $, Lamb 35.00 $, vintage metal lamp/sconces 60.00 $',
         'bounds':'The first three cards in viewport do not establish only three total, completeness, or cheapest price.'},
        {'readable':'Coherent lower listing page and footer; Chevrolet Suburban 24993.00 $, Ford F-150 11993.00 $; 1 selected, 2,3,>,» visible; Contact footer',
         'bounds':'Readable footer is neither blank nor loading; no inference about offscreen query controls or global minimum.'},
        {'readable':'bicycle results, 1 - 12 of 408 listings; first prices 120.00 $, 75.00 $, 199.00 $',
         'bounds':'No claim that first item is cheapest or all matching items have been seen.'},
        {'readable':'guitar results, 1 - 12 of 1573 listings; Complete Guitar Rig Full Stack w/ Perks!!! 900.00 $, 2021 Martin GPC 16e Rosewood 1395.00 $',
         'bounds':'Image-only evidence cannot infer cheapest, uniqueness or task completion.'},
        {'readable':'desk results, 1 - 12 of 1052 listings; OttLite LED Black Desk Lamp with USB for Charging 15.00 $, Standing desk/high dining table/bar 70.00 $, Ergonomic Envoke Desk Chair 280.00 $',
         'bounds':'Desk query also matches a lamp and chair; do not rewrite visible names to fit a query.'},
        {'readable':'Native coherent search interface and explicit There are no results matching message for the displayed fresh query; input field truncates the long string',
         'bounds':'This scoped result does not establish global site absence, loading or task completion.'},
    ]
    private=HERE/'PRIVATE-source-first-expectations.json'
    save(private,{'reviewer':'root, single nonblind source-first review','prediction_seen':False,
        'formal_Mirage_gold_labels':False,'source':'full original 1280x720 PNGs, no transforms',
        'controls':[{'id':'B%02d'%(i+1),'source':name,'image_sha256':sha(HERE/'source-images'/name/'original.png'),**fact}
                    for i,(name,fact)in enumerate(zip(names,facts))]})
    save(HERE/'PRIVATE-source-first-expectations-seal.json',{'file':private.name,'sha256':sha(private),'not_worker_input':True})
    target=HERE/'runtime-package/control-inputs';target.mkdir(exist_ok=False)
    model=json.loads((HERE/'runtime-package/auxiliary-identity-reference.json').read_bytes())['base_model']
    rows=[];bindings=[]
    for i,name in enumerate(names):
        src=HERE/'source-images'/name
        raw=(src/'original.png').read_bytes();request=contract.build_image_only_request(raw,model['repo'],model['revision'])
        path=target/('B%02d.json'%(i+1));save(path,request)
        rows.append({'id':'B%02d'%(i+1),'path':'control-inputs/'+path.name,'sha256':sha(path)})
        bindings.append({'id':rows[-1]['id'],'image_sha256':request['image_sha256'],
            'original_source':name,'source_receipt_sha256':sha(src/'source.json'),
            'original_size':request['original_size'],'new_model_control':True})
    save(HERE/'source-bindings.json',{'sources':bindings,'manual_preparation_not_GUI_task_trial':True,
        'native_capture_collection_sha256':sha(HERE/'source-images/collection.json')})
    save(HERE/'runtime-package/controls-plan.json',{'schema':'bounded-new-image-evidence-controls-v1','auxiliary':rows,
        'limits':{'auxiliary':6,'judge':0,'actor':0,'GUI':0,'scorer':0,'paid_API':0,'format_retries':0},
        'both_models_resident':True,'source_first_private_review_excluded':True,'known_nonblind_development':True,
        'old_completed_controls_not_reexecuted':True,'formal_GUI_or_efficacy':False})
    print(json.dumps({'new_controls':len(rows),'source_first_review_sealed':True,'model_calls':0}))

if __name__=='__main__':main()
