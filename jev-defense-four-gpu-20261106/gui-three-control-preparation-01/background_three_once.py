"""Root-only explicit one-shot background launch; no queue resume or retries."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time,traceback
from pathlib import Path

BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
PACKAGE=BASE/'gui-migration-three-linked02'
PACKAGE_SHA='1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44'
WRAPPER_SHA='e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d'
GROUP='/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799'
SPEC=BASE/'gui-final-readiness-three-01/launch-spec.json'
BATCH=BASE/'gui-batch-image-observer-three-01'
CONTROL=BASE/'gui-outer-control-three-01'
BACKGROUND=BASE/'gui-outer-background-three-01'

def load_wrapper():
    path=PACKAGE/'gui_once.py';assert hashlib.sha256(path.read_bytes()).hexdigest()==WRAPPER_SHA
    sys.path.insert(0,str(PACKAGE))
    spec=importlib.util.spec_from_file_location('fixed_three_outer_wrapper',path)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);g.validate_package(PACKAGE,PACKAGE_SHA)
    return g,path
def validate(g,a):
    g.require(os.getuid()==1015,'Expected owned4090 UID1015')
    g.require(a.spec.resolve()==SPEC,'Only the new exact three-run launch specification is allowed')
    value=g.bound(a.spec,a.spec_sha256)
    g.require(value.get('classification')=='new_exact_original_three_unstarted_trajectories'and value.get('launch_ready')is True,'New spec is not launch-ready')
    g.require(value['package']==str(PACKAGE)and value['package_seal_sha256']==PACKAGE_SHA and
        value['linked']==str(SPEC.parent)and value['batch_root']==str(BATCH),'New spec paths/source differ')
    g.require(value['token_file']=='/data/researcher/jev-defense-four-gpu-20261106/transport-online-three-01/private.token'and
        value['automatic_retry']is False and value['no_legacy_claim_or_root']is True,'New transport or once-only condition differs')
    owner=g.bound(value['ownership_evidence']['path'],value['ownership_evidence']['sha256']);g.ownership(owner,time.time())
    g.require(owner.get('new_online_group')==GROUP and owner.get('wrapper')=={'path':str(PACKAGE/'gui_once.py'),'sha256':WRAPPER_SHA},'Fresh proof belongs to another group/wrapper')
    g.require(not any(path.exists()for path in (BACKGROUND,CONTROL,BATCH,SPEC.parent/'launch-claimed.json')),'A background/control/batch/claim already exists; no duplicate launch')
    return value,owner
def main(a):
    g,wrapper=load_wrapper();value,owner=validate(g,a)
    BACKGROUND.mkdir(exist_ok=False)
    argv=[g.PYTHON,'-B',str(wrapper),'run','--launch-spec',str(SPEC),'--launch-spec-sha256',a.spec_sha256,
        '--control-root',str(CONTROL)]
    g.save(BACKGROUND/'once-only-launch.json',{'argv':argv,'spec_sha256':a.spec_sha256,'wrapper_sha256':WRAPPER_SHA,
        'helper_source_sha256':g.sha(__file__),'parent_identity':g.identity(os.getpid()),'group':GROUP,
        'automatic_retry':False,'native_environment_source_sha256':g.sha(PACKAGE/'native_environment.py'),'time':time.time()})
    try:
        # No HTTP in this helper. The sole child is the SHA-bound wrapper whose
        # real dual health checks occur immediately before its sole GUI Popen.
        g.ownership(owner,time.time())
        with(BACKGROUND/'wrapper.log').open('xb')as log:
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=True,cwd=str(BASE),
                env={**os.environ,**g.NATIVE_ENV,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
        actual=g.identity(child.pid)
        g.save(BACKGROUND/'actualprocess.json',{'identity':actual,'argv':argv,'spec_sha256':a.spec_sha256,
            'wrapper_sha256':WRAPPER_SHA,'time':time.time(),'completion_not_inferred':True})
    except BaseException:
        g.save(BACKGROUND/'launch-failure.json',{'error':traceback.format_exc(),'automatic_retry':False,'time':time.time()});raise
    print(json.dumps({'background':str(BACKGROUND),'actual_wrapper_identity':actual,
        'spec_sha256':a.spec_sha256,'model_GUI_progress_requires_actual_receipts':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--spec-sha256',required=True);main(p.parse_args())
