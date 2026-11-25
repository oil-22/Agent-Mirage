"""Thirty preselected history-retention probes; no GUI actions executed."""
import json,time,traceback
from pathlib import Path
import requests
P=Path('/data/researcher/context-length-pilot-20261117/quant-nf4-02')
R=P/'history-analysis'
H={'Authorization':'Bearer '+(P/'service.token').read_text().strip()}
def save(name,value):
    p=R/name;tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)
def main():
    rows=json.loads((R/'controlled-requests.json').read_text());results=[]
    for i,item in enumerate(rows):
        out=R/(item['id']+'-result.json')
        if out.exists():raise RuntimeError('Do not rerun a completed probe')
        save('controlled-status.json',dict(phase='running',done=i,total=len(rows),current=item['id'],time=time.time()))
        r=requests.post('http://192.0.2.11:19317/generate',json={'body':item['body'],'meta':item['meta']},headers=H,timeout=1200)
        if r.status_code!=200:raise RuntimeError(r.text[:1500])
        result=r.json();save(out.name,result)
        assert result['natural_EOS']
        results.append({k:result[k]for k in ['text','input_tokens','output_tokens','seconds','meta','receipt']})
        print(json.dumps({'done':i+1,'total':len(rows),'id':item['id'],'seconds':result['seconds']}),flush=True)
    save('controlled-results.json',results);save('controlled-status.json',dict(phase='completed',done=len(rows),time=time.time()))
if __name__=='__main__':
    try:main()
    except BaseException:
        save('controlled-failure.json',dict(error=traceback.format_exc(),time=time.time()));raise
