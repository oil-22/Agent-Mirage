import json,hashlib
from pathlib import Path
root=Path(__file__).parent
p=root/'observer-image-review-01/replies.json'; replies=json.loads(p.read_text(encoding='utf-8'))
values=[r['response'] for r in replies]
out={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'forwards':len(values),
 'input_tokens':sum(r['usage']['input_tokens'] for r in values),'output_tokens':sum(r['usage']['output_tokens'] for r in values),
 'seconds_including_audit_sum':sum(r['seconds_including_audit'] for r in values),
 'max_peak_allocated_bytes_on_aux_logical0_phys7':max(r['per_device_memory'][0]['peak_allocated_bytes'] for r in values),
 'max_peak_reserved_bytes_on_aux_logical0_phys7':max(r['per_device_memory'][0]['peak_reserved_bytes'] for r in values),
 'timing_scope':'20 service forward requests including per-request audit; not reservation walltime, total preparation, currency or energy.'}
dest=root/'observer-cost-source-summary.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))
