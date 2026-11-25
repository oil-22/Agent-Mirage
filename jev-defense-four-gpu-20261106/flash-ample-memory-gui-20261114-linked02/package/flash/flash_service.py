"""Authenticated, serial, image-only native Flash service on owned loopback."""
import hmac,json,os,signal,sys,threading,time,traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from gate_core import Journal,digest
from resource_guard import admit,identity,locks,sha
from flash_runtime import FlashRuntime,save
from wire_contract import decode_request,REVISION

class Service:
    def __init__(self,package,root):
        self.package=package;self.root=root;self.config=json.loads((package/'service-config.json').read_bytes())
        self.contract=json.loads((package/'gate-contract.json').read_bytes());self.contract_sha=sha(package/'gate-contract.json')
        if self.config['revision']!=REVISION or self.contract['revision']!=REVISION:raise RuntimeError('Pinned Flash revision required')
        self.token=(root/'token').read_text().strip();self.journal=Journal(root/'journal');self.lock=threading.Lock();self.stopping=threading.Event();self.attempted=0;self.complete=0
        _,fds=locks()
        save(root/'process.json',{**identity(os.getpid()),'visible_devices':os.environ['CUDA_VISIBLE_DEVICES'],'lock_fds':fds,'script_sha256':sha(Path(__file__))})
        self.runtime=FlashRuntime(root,self.config,self.contract)
        self.journal.emit('loaded',{'loaded_sha256':sha(root/'loaded.json'),'contract_sha256':self.contract_sha})
        save(root/'ready.json',{'status':'ready','pid':os.getpid(),'url':'http://127.0.0.1:'+str(self.config['port']),'contract_sha256':self.contract_sha,'revision':REVISION,'independent_single_image':True,'auxiliary_context_history':False,'native_decision_adapter_loaded':True,'created':time.time()})
    def health(self):
        return {**identity(os.getpid()),'status':'stopping'if self.stopping.is_set()else'ready','revision':REVISION,'contract_sha256':self.contract_sha,'actual_ownership':admit(self.config,True),'attempted_calls':self.attempted,'complete_replies':self.complete,'journal_events':self.journal.seq,'journal_head':self.journal.head,'retained_context_entries':0}
    def decision(self,raw):
        request,png=decode_request(raw);rid=request['request_id'];directory=self.root/'requests'/rid
        # mkdir is the persistent, atomic duplicate-ID exclusion. No inference reuse.
        directory.mkdir(exist_ok=False)
        (directory/'wire-request.bin').write_bytes(raw);(directory/'original.png').write_bytes(png)
        self.journal.emit('request_received',{'request_id':rid,'request_sha256':digest(raw),'image_sha256':digest(png)})
        attempted=False
        try:
            if self.stopping.is_set():raise RuntimeError('Service manually stopping')
            save(directory/'admission-before.json',admit(self.config,True));self.attempted+=1;attempted=True
            answer,audit=self.runtime.decide(png,directory)
            save(directory/'admission-after.json',admit(self.config,True))
            save(directory/'audit.json',audit)
            response={'status':'ok','decision':answer,'request_id':rid,'request_sha256':digest(raw),'image_sha256':digest(png),'revision':REVISION,'contract_sha256':self.contract_sha}
            save(directory/'response.json',response);self.complete+=1
            return response
        except BaseException:
            save(directory/'failure.json',{'error':traceback.format_exc(),'native_call_attempted':attempted,'not_a_model_NO':True,'no_automatic_retry':True,'time':time.time()})
            raise
        finally:
            save(directory/'seal.json',{p.name:sha(p)for p in directory.iterdir()if p.is_file()})
            self.journal.emit('request_sealed',{'request_id':rid,'seal_sha256':sha(directory/'seal.json'),'complete':(directory/'response.json').exists(),'native_call_attempted':attempted})

def serve(package):
    root=package/'service';root.mkdir(exist_ok=False);(root/'requests').mkdir()
    import secrets
    fd=os.open(root/'token',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w')as f:f.write(secrets.token_hex(32))
    service=None;server=None;status='technical_failure'
    try:
        service=Service(package,root)
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.0'
            def log_message(self,*args):pass
            def send(self,code,value):
                raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
                self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
            def authorized(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+service.token)
            def do_GET(self):
                if not self.authorized():return self.send(401,{'error':'unauthorized'})
                if self.path!='/health':return self.send(404,{'error':'unknown_endpoint'})
                with service.lock:
                    try:return self.send(200,service.health())
                    except Exception as e:return self.send(503,{'error':str(e),'not_a_model_NO':True})
            def do_POST(self):
                if not self.authorized():return self.send(401,{'error':'unauthorized'})
                if self.path!='/decision':return self.send(404,{'error':'unknown_endpoint'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=16*1024*1024:raise ValueError('Invalid complete request length')
                    raw=self.rfile.read(size)
                    if len(raw)!=size:raise ValueError('Incomplete wire body')
                    decode_request(raw)
                except Exception as e:
                    with service.lock:
                        reject=service.root/'rejected'/(str(time.time_ns())+'.json');reject.parent.mkdir(exist_ok=True)
                        save(reject,{'wire_sha256':digest(raw)if 'raw'in locals()else None,'type':type(e).__name__,'error':str(e),'native_call_attempted':False})
                    return self.send(400,{'error':str(e),'not_a_model_NO':True})
                with service.lock:
                    try:out=service.decision(raw)
                    except FileExistsError:return self.send(409,{'error':'Duplicate request ID; never replayed','not_a_model_NO':True})
                    except Exception as e:return self.send(503,{'error':str(e),'type':type(e).__name__,'not_a_model_NO':True,'no_automatic_retry':True})
                return self.send(200,out)
        server=ThreadingHTTPServer(('127.0.0.1',service.config['port']),Handler)
        server.daemon_threads=False
        def stop(*_):
            service.stopping.set()
            threading.Thread(target=server.shutdown,daemon=True).start()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        print(json.dumps({'ready':True,'pid':os.getpid(),'port':service.config['port']}),flush=True)
        server.serve_forever(poll_interval=0.25);status='manually_stopped'
    except BaseException:
        save(root/'failure.json',{'error':traceback.format_exc(),'not_a_model_NO':True,'no_automatic_restart':True});traceback.print_exc()
    finally:
        if server is not None:server.server_close()
        if service is not None:
            service.journal.emit('service_terminal',{'status':status,'attempted_calls':service.attempted,'complete_replies':service.complete})
            save(root/'terminal.json',{'status':status,'attempted_calls':service.attempted,'complete_replies':service.complete,'journal_events':service.journal.seq,'journal_head':service.journal.head,'time':time.time()})
        sys.stdout.flush();sys.stderr.flush()
    return 0 if status=='manually_stopped'else 1

if __name__=='__main__':raise SystemExit(serve(Path(sys.argv[1]).resolve()))
