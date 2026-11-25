import hashlib
import http.server
import json
import pathlib
import threading
import time
import uuid
import sys
import urllib.request

MODELS=['Qwen3.5-9B','GLM-4.6V-Flash-411bb4d77144']
if sys.argv[1]=='serve':
    root=pathlib.Path('/data/researcher/models')
    files={str(p.relative_to(root)):p for model in MODELS for p in (root/model).glob('*') if p.is_file()}
    token=uuid.uuid4().hex
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.client_address[0]!='192.0.2.11' or not self.path.startswith('/'+token+'/'):
                self.send_error(404); return
            name=self.path[len(token)+2:]
            if name=='index':
                data=json.dumps({n:p.stat().st_size for n,p in files.items()}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if name=='shutdown':
                self.send_response(200);self.end_headers();threading.Thread(target=self.server.shutdown).start();return
            if name not in files:
                self.send_error(404);return
            p=files[name]
            self.send_response(200);self.send_header('Content-Length',str(p.stat().st_size));self.end_headers()
            with p.open('rb') as f:
                while b:=f.read(4*1024*1024):self.wfile.write(b)
    server=http.server.ThreadingHTTPServer(('192.0.2.10',0),Handler)
    state={'url':f'http://192.0.2.10:{server.server_port}/{token}/','files':len(files),'started':time.time()}
    pathlib.Path('/data/researcher/attention-audit-20261031/model-transfer-endpoint.json').write_text(json.dumps(state))
    threading.Timer(1800,server.shutdown).start()
    server.serve_forever()
    server.server_close()
    sys.exit(0)
else:
    base=sys.argv[2]
    root=pathlib.Path('/home/researcher/models')
    index=json.load(urllib.request.urlopen(base+'index'))
    log=[]
    for name,size in index.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() and p.stat().st_size==size:
            continue
        started=time.time()
        with urllib.request.urlopen(base+name,timeout=60) as response,p.open('wb') as f:
            while b:=response.read(4*1024*1024):f.write(b)
        assert p.stat().st_size==size
        log.append({'file':name,'bytes':size,'seconds':round(time.time()-started,2)})
        pathlib.Path('/home/researcher/model-transfer-20261031.json').write_text(json.dumps(log,indent=2))
        print(log[-1],flush=True)
    urllib.request.urlopen(base+'shutdown').read()
