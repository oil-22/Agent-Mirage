"""Authenticated serial restart transport using the restored, unchanged LocalQwen."""
import argparse,base64,hashlib,hmac,json,os,pathlib,signal,time,traceback
from http.server import BaseHTTPRequestHandler,HTTPServer
from defense.core import PublicView,VisibleImage,digest
from defense.qwen_backend import LocalQwen

def main(a):
 root=a.root;state={'pid':os.getpid(),'uid':os.getuid(),'phase':'loading','started':time.time(),'physical_gpus':[1,2,3,4]}
 def save(p,x):
  temp=p.with_suffix('.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2));temp.replace(p)
 save(root/'status.json',state)
 model=LocalQwen('/data/llms/Qwen3.8-27B',root/'runtime.json',placement='balanced')
 expected=json.loads((a.package/'original-runtime.json').read_bytes());assert model.runtime['metadata_sha256']==expected['metadata_sha256']
 assert model.runtime['torch']==expected['torch'] and model.runtime['transformers']==expected['transformers']
 assert all(p.device.type=='cuda'for p in model.model.parameters())
 assert all(p.device.type=='cuda'for p in model.model.buffers())
 devices={str(p.device)for p in model.model.parameters()};assert len(devices)==4
 save(root/'actual-device-audit.json',{'devices':sorted(devices),'all_parameters_and_buffers_cuda':True,'dtype':str(model.model.dtype),'history_truncation':False,'placement_change':'Four currently free3090 cards vs original five; no bitwise or cost equivalence claim','CUDA_VISIBLE_DEVICES':os.environ['CUDA_VISIBLE_DEVICES']})
 token=a.token_file.read_text().strip();stop={'value':False};signal.signal(signal.SIGUSR1,lambda *_:stop.update(value=True))
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,code,value):
   raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def auth(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
  def do_GET(self):
   if not self.auth():self.send(403,{'error':'unauthorized'});return
   self.send(200,{'phase':state['phase'],'dtype':'BF16','backend':'sdpa','pid':os.getpid()})
  def do_POST(self):
   if not self.auth():self.send(403,{'error':'unauthorized'});return
   n=int(self.headers.get('Content-Length','0'));assert 0<n<=64*1024**2
   out=root/'requests'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False);raw=self.rfile.read(n);(out/'request.json').write_bytes(raw)
   try:
    body=json.loads(raw);assert body['operation']=='judge','This scoped restart admits no actor or GUI request'
    v=body['view'];view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(x['raw_base64']),x['role'])for x in v['images']),v.get('recent_action',''),v.get('execution_feedback',''),v['observed_at'])
    text=model.judge(body['system'],view,body.get('candidate'),out/'generation.json');rec=json.loads((out/'generation.json').read_bytes())
    result={'verdict':text,'receipt':str(out),'input_tokens':len(rec['input_ids']),'output_tokens':len(rec['generated_ids']),'seconds':rec['seconds']};save(out/'response.json',result);self.send(200,result)
   except BaseException:
    error={'error':traceback.format_exc(),'receipt':str(out),'semantic_mirage':None};save(out/'failure.json',error);self.send(500,error)
 server=HTTPServer(('127.0.0.1',18127),Handler);server.timeout=1;state.update(phase='ready',ready_at=time.time());save(root/'status.json',state)
 while not stop['value']:server.handle_request()
 server.server_close();state.update(phase='stopped_at_request_boundary',ended=time.time());save(root/'status.json',state)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--package',type=pathlib.Path,required=True);p.add_argument('--token-file',type=pathlib.Path,required=True);main(p.parse_args())
