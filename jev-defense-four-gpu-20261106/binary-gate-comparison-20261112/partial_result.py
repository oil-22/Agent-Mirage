"""Read completed model decisions; PRIVATE labels join locally only."""
import hashlib,json,sys,time
from pathlib import Path
from manage import HERE,remote,save,sha
model=sys.argv[1];assert model in ['flash','neohorse','style']
assert not (HERE/('partial-'+model+'.json')).exists()
if not (HERE/'selection-rule-read-commitment.json').exists():
 save(HERE/'selection-rule-read-commitment.json',{'sha256':sha(HERE/'selection-rule-pre-metrics.json'),'first_metric_read_after':time.time(),'labels_sha256':sha(HERE/'PRIVATE-labels-pre-output.json')})
code=r'''
from pathlib import Path
import hashlib,json
R=Path('/home/researcher/jev-defense-four-gpu-20261106/binary-gate-comparison-20261112')
model=MODEL
root=R/'results'/model
t=json.loads((root/'terminal.json').read_bytes());assert t['status']=='completed' and t['complete_replies']==18
rows=[]
for d in sorted((root/'requests').iterdir()):
 seal=json.loads((d/'seal.json').read_bytes())
 for n in ['request.json','response.json','native-result.json','forward-trace.json']:
  assert hashlib.sha256((d/n).read_bytes()).hexdigest()==seal[n]
 rows.append(json.loads((d/'response.json').read_bytes()))
print(json.dumps({'model':model,'terminal':t,'rows':rows}))
'''.replace('MODEL',repr(model))
out,d=remote(code,'completed-'+model+'-decisions');v=json.loads(out)
labels={r['id']:r for r in json.loads((HERE/'PRIVATE-labels-pre-output.json').read_bytes())['rows']}
errors=[];bound=[]
for row in v['rows']:
 l=labels[row['case_id']];assert l['image_sha256']==row['image_sha256']
 if l['expected'] is None:bound.append({'id':row['case_id'],'answer':row['answer'],'p_yes':row['probabilities']['YES']})
 elif l['expected']!=row['answer']:errors.append({'id':row['case_id'],'stratum':l['stratum'],'expected':l['expected'],'answer':row['answer'],'p_yes':row['probabilities']['YES']})
result={'model':model,'complete':18,'errors':errors,'boundary':bound,'evidence':str(d),'actual_tensor_reload_and_raw_logit_audit_pending':True,'new_model_calls':0}
save(HERE/('partial-'+model+'.json'),{'summary':result,'received':v});print(json.dumps(result,ensure_ascii=False))
