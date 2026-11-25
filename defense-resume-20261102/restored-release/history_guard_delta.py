"""Re-evaluate a narrower controller override with byte-bound frozen model replies.

No model HTTP requests. Original failed labels remain in their original release.
"""
import argparse,hashlib,json,runpy,sys
from pathlib import Path
import defense.http_backend as backend
from defense.core import canonical,digest

ap=argparse.ArgumentParser();ap.add_argument('--replay-source',type=Path,required=True)
a,remaining=ap.parse_known_args();source=a.replay_source
summary=json.loads((source/'summary.json').read_text());assert summary['phase']=='completed'and not summary['passed']
records=[]
for path in source.glob('*/events.jsonl'):
    events=[json.loads(l)for l in path.read_text().splitlines()]
    for i,event in enumerate(events):
        if event['kind']!='verifier_request':continue
        req=event['data'];raw=next(e for e in events[i+1:]if e['kind']=='verifier_raw')
        records.append({'system':req['system'],'public':req['public'],'candidate':req['candidate'],
            'raw':raw['data']['response'],'source':str(path),'source_sha256':digest(path.read_bytes()),'source_raw_sha256':raw['sha256']})

class FrozenReplies:
    def __init__(self,url,token_file):
        assert url=='http://192.0.2.11:18127';self.calls=[]
    def judge(self,system,view,candidate=None):
        bound={'system':system,'public':view.data(),'candidate':candidate}
        rows=[r for r in records if canonical({k:r[k]for k in bound})==canonical(bound)]
        assert len(rows)==1,'Frozen input mismatch; no new inference is allowed'
        r=rows[0];self.calls.append({'frozen_model_reply_reused':True,'source':r['source'],
            'source_sha256':r['source_sha256'],'source_raw_sha256':r['source_raw_sha256'],
            'full_input_binding_sha256':digest(canonical(bound))})
        return r['raw']
backend.RemoteQwen=FrozenReplies
sys.argv=[str(Path(__file__).with_name('history_report_delta.py')),*remaining]
runpy.run_path(sys.argv[0],run_name='__main__')
root=Path(remaining[remaining.index('--root')+1]);out=root/'summary.json'
result=json.loads(out.read_text());result['new_inference_calls']=0
result['scope']='Controller comparison-scope delta only. Three exact-input frozen model replies reused; two comparative overrides retained without model calls. No GUI, new model inference, held-out accuracy or independent Mirage labels.'
result['reused_source_summary_sha256']=digest((source/'summary.json').read_bytes())
out.write_text(json.dumps(result,indent=2))
