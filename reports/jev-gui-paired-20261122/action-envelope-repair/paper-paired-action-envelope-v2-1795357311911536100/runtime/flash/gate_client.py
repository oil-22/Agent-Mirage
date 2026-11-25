"""Image-only loopback client; every call has a new ID and no response cache."""
import base64,json,math,uuid,urllib.request
from pathlib import Path
from gate_core import Decision,digest

class FlashClient:
    def __init__(self,url,token_file,*,revision,contract_sha256,timeout=120):
        if not url.startswith('http://127.0.0.1:'):raise ValueError('Use a verified loopback endpoint/SSH tunnel')
        self.url=url.rstrip('/');self.token_file=Path(token_file);self.revision=revision;self.contract_sha256=contract_sha256;self.timeout=timeout
    def decide(self,png):
        if not isinstance(png,bytes)or not png.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Original complete PNG required')
        rid=uuid.uuid4().hex
        body={'request_id':rid,'image_png_base64':base64.b64encode(png).decode(),'image_sha256':digest(png)}
        raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        req=urllib.request.Request(self.url+'/decision',data=raw,headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token_file.read_text().strip()})
        # No HTTP/model retry and no exact-image result reuse.
        with urllib.request.urlopen(req,timeout=self.timeout)as r:out=json.load(r)
        if out.get('request_id')!=rid or out.get('request_sha256')!=digest(raw) or out.get('image_sha256')!=digest(png):raise ValueError('Response request/image binding mismatch')
        if out.get('revision')!=self.revision or out.get('contract_sha256')!=self.contract_sha256 or out.get('decision')not in {'YES','NO'}:raise ValueError('Response model/contract/decision mismatch')
        return Decision(out['decision'],out['image_sha256'],rid,out['revision'],out['contract_sha256'])
