"""Explicit root-invoked evidence binding and prepare only; no HTTP or Popen."""
import argparse,hashlib,importlib.util,json,os,sys,time,traceback
from pathlib import Path
from types import SimpleNamespace

BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
PACKAGE=BASE/'gui-migration-three-linked02'
PACKAGE_SHA='1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44'
WRAPPER_SHA='e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d'
GROUP='/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799'
REVIEWED_SPEC_SHA='233850b6bf6ecac89fbd18452c592a5b2481eeee9f5eaf6eea8b9af23c083e8c'
BATCH=BASE/'gui-batch-image-observer-three-01'
LINKED=BASE/'gui-final-readiness-three-01'
RESOURCE_FLAGS=('decoder_layers14_22_22_6','allocator_expandable_segments','new_capacity_not_old15720','all_three_same_resource')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def save(p,obj):
    with Path(p).open('x',encoding='utf8')as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def file_bound(item):
    p=Path(item['path']);require(not p.is_symlink()and sha(p)==item['sha256'],'Evidence file SHA differs: '+str(p))
def load_wrapper(package=PACKAGE):
    package=Path(package);wrapper=package/'gui_once.py'
    require(sha(wrapper)==WRAPPER_SHA,'Fixed reviewed wrapper changed')
    sys.path.insert(0,str(package))
    spec=importlib.util.spec_from_file_location('fixed_three_gui_once',wrapper)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    g.validate_package(package,PACKAGE_SHA)
    return g
def validate_resource(resource):
    require(resource.get('group')==GROUP,'Resource proof must name the exact new online group')
    require(resource.get('reviewed_spec_sha256')==REVIEWED_SPEC_SHA,'New reviewed runtime specification differs')
    require(json.dumps(resource.get('decoder_layer_counts'))==json.dumps([14,22,22,6])and
        resource.get('allocator')=='expandable_segments:True','Actual decoder layer allocation/allocator differs')
    require(all(resource.get(key)is True for key in RESOURCE_FLAGS),'Actual resource prerequisite false/missing')
    sources=resource.get('source_evidence');require(isinstance(sources,list)and bool(sources),'Resource source_evidence is required')
    require(all(isinstance(row,dict)and set(row)>={'path','sha256'}for row in sources),'Malformed resource source binding')
    for item in sources:file_bound(item)
def validate_owner(g,owner,now):
    g.ownership(owner,now)
    require(owner.get('new_online_group')==GROUP,'Fresh ownership names a different online group')
    require(owner.get('wrapper')=={'path':str(PACKAGE/'gui_once.py'),'sha256':WRAPPER_SHA},'Fresh ownership names a different wrapper')
def make_bindings(template,resource_item,owner_item):
    require(template.get('launch_ready')is False,'Use the immutable closed template')
    require(set(template['evidence']).isdisjoint({'ownership_transport','resource_conditions'}),'Closed template unexpectedly contains fresh evidence')
    bindings=json.loads(json.dumps(template['evidence']))
    bindings['resource_conditions']=dict(resource_item);bindings['ownership_transport']=dict(owner_item)
    return bindings
def main(a):
    require(os.getuid()==1015,'Expected owned4090 UID1015')
    require(not a.output.exists()and not BATCH.exists()and not LINKED.exists(),'New output/batch/linked roots required')
    g=load_wrapper()
    resource=g.bound(a.resource,a.resource_sha256);validate_resource(resource)
    owner=g.bound(a.ownership,a.ownership_sha256);validate_owner(g,owner,time.time())
    template=json.loads((PACKAGE/'readiness.template.json').read_bytes())
    bindings=make_bindings(template,{'path':str(a.resource.resolve()),'sha256':a.resource_sha256},
        {'path':str(a.ownership.resolve()),'sha256':a.ownership_sha256})
    for item in bindings.values():file_bound(item)
    # The new directory is the persistent once-only preparation attempt. Failures
    # keep it and need a new source-linked root; no retry or old claim is reused.
    a.output.mkdir(parents=True,exist_ok=False)
    save(a.output/'evidence-bindings.json',bindings)
    save(a.output/'preparation-claim.json',{'helper_sha256':sha(__file__),'package_seal_sha256':PACKAGE_SHA,
        'wrapper_sha256':WRAPPER_SHA,'resource_sha256':a.resource_sha256,'ownership_sha256':a.ownership_sha256,
        'group':GROUP,'new_GUI_calls_before_prepare':0,'automatic_retry':False,'time':time.time()})
    try:
        # No HTTP/model/GUI in prepare. The sealed wrapper rechecks all actual
        # gates and native environment, then writes a fresh independent spec.
        validate_owner(g,owner,time.time())
        result=g.prepare(SimpleNamespace(package=PACKAGE,package_seal_sha256=PACKAGE_SHA,
            evidence_bindings=a.output/'evidence-bindings.json',evidence_bindings_sha256=sha(a.output/'evidence-bindings.json'),
            batch_root=BATCH,output=LINKED))
        save(a.output/'result.json',{**result,'group':GROUP,'background_not_started':True,
            'HTTP_model_GUI_scorer_signal_calls':0,'time':time.time()})
    except BaseException:
        save(a.output/'failure.json',{'error':traceback.format_exc(),'automatic_retry':False,
            'HTTP_model_GUI_scorer_signal_calls':0,'time':time.time()});raise
    finally:save(a.output/'seal.json',{p.name:sha(p)for p in a.output.iterdir()if p.is_file()})
    print(json.dumps({'output':str(a.output),**result,'background_not_started':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('resource','ownership','output'):p.add_argument('--'+key,type=Path,required=True)
    for key in ('resource-sha256','ownership-sha256'):p.add_argument('--'+key,required=True)
    main(p.parse_args())
