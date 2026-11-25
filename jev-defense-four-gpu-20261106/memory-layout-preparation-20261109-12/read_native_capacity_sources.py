"""Read sealed native layout and code only; no GPU or model construction."""
from pathlib import Path
import json
import sys
import time

HERE=Path(__file__).resolve().parent
GUI=HERE.parent/'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0,str(GUI))
from remote_control import remote,save,sha

CODE=r'''
from pathlib import Path
import collections,hashlib,json,os,time
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
package=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/full-gui-bounded-evidence-20261109-03')
ref=json.loads((package/'primary-reference.json').read_bytes())
bound_path=Path(ref['primary_native_layout_receipt']);assert sha(bound_path)==ref['primary_native_layout_receipt_sha256']
bound=json.loads(bound_path.read_bytes());meta=Path(bound['meta_root'])
for name,expected in json.loads((meta/'seal.json').read_bytes()).items():assert sha(meta/name)==expected
state=json.loads((meta/'meta-state.json').read_bytes())
source=Path('/opt/whz/conda-envs/webmall-vlm/lib/python3.11/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py')
assert sha(source)==bound['native_source_sha256']
layers={i:sum(x['bytes']for x in state if x['name'].startswith('model.language_model.layers.'+str(i)+'.'))for i in range(64)}
other=collections.Counter()
for row in state:
 if any(row['name'].startswith('model.language_model.layers.'+str(i)+'.')for i in range(64)):continue
 key='model.visual'if row['name'].startswith('model.visual.')else row['name'].rsplit('.',1)[0]
 other[key]+=row['bytes']
assert sum(layers.values())+sum(other.values())==54713457120
def layout(first,second,vision):
 values={0:0,1:0,2:0,3:0}
 for row in state:
  name=row['name']
  if name.startswith('model.visual.'):device=vision
  elif name.startswith('model.language_model.embed_tokens.'):device=0
  elif name.startswith('model.language_model.layers.'):
   number=int(name.split('.')[3]);device=0 if number<first else 1 if number<second else 2
  else:device=2
  values[device]+=row['bytes']
 return values
choices=[]
for first in range(12,28):
 for second in range(max(first+12,32),54):
  values=layout(first,second,3)
  choices.append({'first_cut':first,'second_cut':second,'layer_counts':[first,second-first,64-second],'parameter_bytes':values,'largest_language_device_bytes':max(values[i]for i in range(3))})
best=sorted(choices,key=lambda x:(x['largest_language_device_bytes'],max(x['layer_counts'])-min(x['layer_counts'])))[:5]
text=source.read_text();lines=text.splitlines()
snippets=[]
for i,line in enumerate(lines):
 if any(term in line for term in ['image_embeds = image_embeds.to(', 'inputs_embeds = inputs_embeds.masked_scatter', 'core_attn_out = core_attn_out.transpose', 'def get_image_features(']):
  snippets.append({'line':i+1,'text':'\n'.join(lines[max(0,i-4):i+10])})
print(json.dumps({'time':time.time(),'UID':os.getuid(),'read_only':True,'new_model_GPU_GUI_calls':0,
 'native_model_source_sha256':sha(source),'meta_state_sha256':sha(meta/'meta-state.json'),
 'total_parameter_bytes':54713457120,'layer_bytes':layers,'nonlayer_bytes':dict(other),
 'original_19_24_21_vision0':layout(19,43,0),
 'candidate_shared_visual3_layouts':best,'candidates_are_parameter_capacity_only_not_activation_or_KV_fit':True,
 'auxiliary_stays_one_9B_GPU_model_not_CPU_inference':True,
 'native_cross_device_and_failure_site_source':snippets,
 'RAM_meminfo':Path('/proc/meminfo').read_text()}))
'''

if __name__=='__main__':
    output,operation=remote('3090',CODE,'read-native-layer-byte-inventory-and-vision-device-transport',timeout=55)
    value=json.loads(output);target=HERE/('source-inspection-'+str(time.time_ns()));target.mkdir(exist_ok=False)
    save(target/'receipt.json',{'operation':str(operation),'result':value})
    print(json.dumps({'receipt':str(target/'receipt.json'),'sha256':sha(target/'receipt.json'),
      'current_layout_parameter_bytes':value['original_19_24_21_vision0'],
      'candidate_layouts':value['candidate_shared_visual3_layouts'],
      'nonlayer_bytes':value['nonlayer_bytes'],'new_model_GPU_GUI_calls':0},ensure_ascii=False))
