import hashlib,io,json,pathlib
from PIL import Image
root=pathlib.Path('/home/researcher/attention-20261031');root.mkdir(exist_ok=True)
assets=root/'preflight-assets';assets.mkdir(exist_ok=True)
buf=io.BytesIO();Image.new('RGB',(336,336),'white').save(buf,format='PNG');data=buf.getvalue();h=hashlib.sha256(data).hexdigest();(assets/h[:2]).mkdir(exist_ok=True);(assets/h[:2]/(h+'.png')).write_bytes(data)
cases=[]
for mode in ['text','image']:
    contents=[{'type':'text','text':'Current task: describe whether visual evidence is available. Give one sentence, then Action: wait().'}]
    if mode=='image':contents.append({'type':'image_url','image_url':{'url':'archive-image://sha256/'+h}})
    req={'messages':[{'role':'system','content':'Use only supplied observations. Do not claim unavailable visual facts.'},{'role':'user','content':'Previous screenshot observation (image not retained).'},{'role':'assistant','content':'Thought: The prior image was unavailable.\nAction: wait().'},{'role':'user','content':contents}]}
    cases.append({'id':'preflight-'+mode,'task':'technical','app':'technical','stage':'preflight','step':2,'history':'full','condition':mode,'request':req})
(root/'preflight-plan.json').write_text(json.dumps({'max_new_tokens':128,'cases':cases}))
