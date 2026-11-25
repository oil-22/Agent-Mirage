"""Capacity-only replay; historical BF16 inputs are not experiment trajectories."""
import json,time,traceback
from pathlib import Path
import requests
P=Path(__file__).resolve().parent
URL='http://192.0.2.11:19317'
HEAD={'Authorization':'Bearer '+(P/'service.token').read_text().strip()}

def save(name,value):
    p=P/name;tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def main():
    source=json.loads((P/'capacity-source.json').read_text());results=[]
    save('capacity-status.json',dict(phase='waiting_for_model',time=time.time()))
    for _ in range(180):
        if (P/'model-output/startup-failure.json').exists():raise RuntimeError('Model startup failed')
        try:
            r=requests.get(URL+'/health',headers=HEAD,timeout=5)
            if r.status_code==200 and r.json().get('ready'):break
        except requests.RequestException:pass
        time.sleep(2)
    else:raise RuntimeError('Model readiness timeout')
    for label in ['26k','40k']:
        raw=json.loads(Path(source['request_'+label]).read_text())
        body=raw['body'] if label=='26k' else raw
        save('capacity-status.json',dict(phase='generating',probe=label,time=time.time()))
        started=time.time()
        r=requests.post(URL+'/generate',headers=HEAD,json=dict(body=body,meta=dict(stage='capacity_only',label=label,
            source=source['request_'+label],not_experiment_result=True)),timeout=1200)
        if r.status_code!=200:raise RuntimeError('Capacity request failed: '+r.text[:1600])
        out=r.json();save('capacity-'+label+'-response.json',out)
        assert out['input_tokens']==source['expected_'+label]
        assert out['natural_EOS'],'Capacity response hit output cap'
        result={k:out[k] for k in ['input_tokens','output_tokens','natural_EOS','seconds','peak_allocated_bytes','receipt']}
        result['label']=label;results.append(result);print(json.dumps(result),flush=True)
    approved=dict(passed=True,scope='These two exact requests only; not a guarantee for every future history',
        probes=results,quantization='NF4 double quantization, BF16 compute',time=time.time())
    save('capacity-approved.json',approved);save('capacity-status.json',dict(phase='passed',**approved))

if __name__=='__main__':
    try:main()
    except BaseException:
        save('capacity-failure.json',dict(error=traceback.format_exc(),time=time.time()))
        save('capacity-status.json',dict(phase='failed',time=time.time()));raise
