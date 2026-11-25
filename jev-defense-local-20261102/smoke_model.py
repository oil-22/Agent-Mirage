import argparse,json,pathlib,time,traceback
from defense.core import VisibleImage,digest
from jev_auxiliary import LocalDecisionClient
p=argparse.ArgumentParser();p.add_argument('model');a=p.parse_args();B=pathlib.Path(__file__).resolve().parent
root=B/'smoke'/a.model;root.mkdir(parents=True,exist_ok=False)
image=next((B/'images').glob('25c9*.png'));raw=image.read_bytes();(root/'original.png').write_bytes(raw)
client=LocalDecisionClient(a.model,'http://127.0.0.1:'+('18221' if a.model=='jev_style' else '18222'),B/'transport.token')
try:
    result=client.decide(VisibleImage(raw),'keyword_focus',{'observation_id':'smoke-focus-filled','scope':'single_original_frame','image_sha256':digest(raw),'development_only':True})
    (root/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['model','answer','probabilities','original_size','native_result','seconds_including_audit','peak_allocated_bytes']}),flush=True)
except Exception:
    (root/'failure.txt').write_text(traceback.format_exc());raise
finally:
    (root/'seal.json').write_text(json.dumps({x.name:digest(x.read_bytes()) for x in root.iterdir() if x.is_file()},indent=2))
