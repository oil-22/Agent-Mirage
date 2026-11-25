"""Serial, authenticated local inference transport; no environment access."""
import argparse,base64,fcntl,hmac,json,os,signal,subprocess,time,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from defense.core import PublicView,VisibleImage,digest
from defense.qwen_backend import LocalQwen
def save(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2));t.replace(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);ap.add_argument('--gate-shadow',type=Path,required=True);ap.add_argument('--port',type=int,default=18127);ap.add_argument('--placement',choices=['auto','balanced'],default='auto');a=ap.parse_args()
 a.root.mkdir(parents=True,exist_ok=True);lock=(a.root/'service.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 state={'pid':os.getpid(),'phase':'waiting_preflight','gate':str(a.gate_shadow),'started':time.time()};save(a.root/'status.json',state)
 while True:
  gate=json.loads(a.gate_shadow.read_text())
  if gate['phase']=='preflight_failed':raise RuntimeError('Verifier preflight failed; online launch remains gated')
  if gate['phase']=='completed':
   assert gate['completed_cases']==20 and gate['failed_cases']==0;break
  time.sleep(5)
 requested_gpus=[int(gpu)for gpu in os.environ.get('CUDA_VISIBLE_DEVICES','0,1,2,3').split(',')]
 assert requested_gpus and len(set(requested_gpus))==len(requested_gpus)
 for waiting in range(60):
  used=[int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())for gpu in requested_gpus]
  if max(used)<1024:break
  time.sleep(2)
 else:raise RuntimeError(f'Requested GPUs have not been released: {used}')
 token=a.token_file.read_text().strip();assert len(token)>=32
 state.update(phase='loading');save(a.root/'status.json',state)
 model=LocalQwen('/data/llms/Qwen3.8-27B',a.root/'runtime.json',placement=a.placement)
 expected=json.loads((a.gate_shadow.parent/'runtime.json').read_text())
 assert model.runtime['metadata_sha256']==expected['metadata_sha256']
 stop={'value':False};signal.signal(signal.SIGUSR1,lambda *_:stop.update(value=True))
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,code,value):
   raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def authorized(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
  def do_GET(self):
   if not self.authorized():self.send(403,{'error':'unauthorized'});return
   self.send(200,{'phase':state['phase'],'model':'/data/llms/Qwen3.8-27B','dtype':'BF16','backend':'sdpa','verifier_grammar':'lm-format-enforcer-0.11.3','actor_grammar':False})
  def do_POST(self):
   if not self.authorized():self.send(403,{'error':'unauthorized'});return
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=64*1024**2:self.send(413,{'error':'request_size_limit_no_truncation'});return
   out=a.root/'requests'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
   raw=self.rfile.read(size);(out/'request.json').write_bytes(raw)
   try:
    body=json.loads(raw)
    if body['operation']=='actor':
     original=body['body'];text=model.generate(original['messages'],original['max_tokens'],out/'generation.json',original_body=original);result={'text':text}
    elif body['operation']=='judge':
     v=body['view'];view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(x['raw_base64']),x['role'])for x in v['images']),v.get('recent_action',''),v.get('execution_feedback',''),v['observed_at'])
     result={'verdict':model.judge(body['system'],view,body.get('candidate'),out/'generation.json')}
    else:raise ValueError('Unknown operation')
    rec=json.loads((out/'generation.json').read_text());result.update(receipt=str(out),input_tokens=len(rec['input_ids']),output_tokens=len(rec['generated_ids']),seconds=rec['seconds'])
    save(out/'response.json',result);self.send(200,result)
   except Exception:
    error={'error':traceback.format_exc(),'receipt':str(out),'semantic_mirage':None};save(out/'failure.json',error);self.send(500,error)
 server=HTTPServer(('0.0.0.0',a.port),Handler);server.timeout=1
 state.update(phase='ready',port=a.port,updated=time.time());save(a.root/'status.json',state)
 while not stop['value']:server.handle_request()
 server.server_close();state.update(phase='stopped_at_request_boundary',updated=time.time());save(a.root/'status.json',state)
if __name__=='__main__':main()
