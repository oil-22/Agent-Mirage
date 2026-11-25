"""Only legitimate delivered inputs cross the inference boundary."""
import base64,copy,json,time
import requests
from .core import InferenceFailure
class RemoteQwen:
 def __init__(self,url,token_file):
  from pathlib import Path
  self.url=url;self.headers={'Authorization':'Bearer '+Path(token_file).read_text().strip()};self.calls=[]
 def call(self,body):
  try:r=requests.post(self.url,json=body,headers=self.headers,timeout=(15,1800))
  except requests.RequestException as error:
   record={'operation':body['operation'],'transport_failure':str(error)};self.calls.append(record);raise InferenceFailure(json.dumps(record))from error
  try:data=r.json()
  except ValueError as error:raise InferenceFailure('Inference returned non-JSON transport body; HTTP '+str(r.status_code))from error
  self.calls.append({k:v for k,v in data.items()if k not in {'text','verdict'}})
  if not r.ok:raise InferenceFailure(json.dumps({'http_status':r.status_code,'receipt':data.get('receipt'),'error':data.get('error'),'semantic_mirage':None}))
  return data
 def actor(self,body):return self.call({'operation':'actor','body':body})['text']
 def judge(self,system,view,candidate=None):
  value=view.data();value['images']=[{'raw_base64':base64.b64encode(x.raw).decode(),'role':x.role}for x in view.images]
  return self.call({'operation':'judge','system':system,'view':value,'candidate':candidate})['verdict']
 def health(self):
  r=requests.get(self.url,headers=self.headers,timeout=10);r.raise_for_status();return r.json()
