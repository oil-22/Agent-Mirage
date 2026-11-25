import pathlib,json,requests,time
p=pathlib.Path('/data/researcher/context-length-pilot-20261117/quant-nf4-01');source='/data/researcher/jev-defense-four-gpu-20261106/flash-four-injection-defense-20261115-04/primary/requests/00138/body.json'
body=json.loads(pathlib.Path(source).read_text());h={'Authorization':'Bearer '+(p/'service.token').read_text().strip()}
(p/'capacity-50k-status.json').write_text(json.dumps({'phase':'generating','source':source,'time':time.time()}))
r=requests.post('http://192.0.2.11:19317/generate',headers=h,json={'body':body,'meta':{'stage':'capacity_only','label':'50k-upper-trajectory-probe','not_experiment_result':True,'source':source}},timeout=1200)
(p/'capacity-50k-response.json').write_text(r.text)
if r.status_code!=200:
 print(r.text[-1800:]);raise RuntimeError('50k capacity failure')
d=r.json();v={k:d[k]for k in ['input_tokens','output_tokens','natural_EOS','seconds','peak_allocated_bytes']};v['passed']=bool(d['natural_EOS']);(p/'capacity-50k-status.json').write_text(json.dumps(v));print(json.dumps(v))
