import argparse,hashlib,json,pathlib,sys,tempfile,time
import torch,transformers
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--model',required=True);a=p.parse_args()
B=pathlib.Path(__file__).resolve().parent;dest=B/'models-verified'/a.model
image=next(pathlib.Path('/home/researcher/defense-resume-20261102-retry2/images').glob('564e*.png')) if pathlib.Path('/home/researcher/defense-resume-20261102-retry2/images').exists() else next((B/'images').glob('564e*.png'))
if a.model=='jev_style':
    sys.path.insert(0,str(dest));from jev_style_decision import JevStyleDecision
    from macjev.vision import prepare_image,ImageLoader
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5ForConditionalGeneration
    with tempfile.TemporaryDirectory(dir=B) as td:
        info=prepare_image(Image.open(image),pathlib.Path(td),budget_px=1638400)
        pv,grid=ImageLoader(dest)(info['path']);grid=grid.tolist()
else:
    sys.path.insert(0,str(dest/'package/src'));from neohorse_decision.vision import VisionDecisionEngine
    from transformers.models.qwen2_vl.image_processing_pil_qwen2_vl import Qwen2VLImageProcessorPil
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Model
    proc=Qwen2VLImageProcessorPil.from_pretrained(dest/'backbone',local_files_only=True,size={'shortest_edge':65536,'longest_edge':1048576})
    batch=proc(images=Image.open(image).convert('RGB'),return_tensors='pt');pv=batch['pixel_values'];grid=batch['image_grid_thw'][0].tolist()
result={'model':a.model,'time':time.time(),'torch':torch.__version__,'transformers':transformers.__version__,'python':sys.version,'original_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'original_size':list(Image.open(image).size),'native_grid_thw':grid,'pixel_tensor_shape':list(pv.shape),'weights_loaded':False,'GPU_inference':False}
print(json.dumps(result),flush=True)
with(B/('cpu-import-'+a.model+'-'+str(time.time_ns())+'.json')).open('x') as f:json.dump(result,f,indent=2)
