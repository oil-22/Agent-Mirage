"""Seal manually reviewed public candidates before joining checker/execution outcomes."""
import argparse,hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development';sha=lambda b:hashlib.sha256(b).hexdigest()
def record(seq,label,native_error,note):
    pointer=json.loads((PREP/'public-candidates-current.json').read_bytes());source=Path(pointer['directory'])
    assert sha((source/'sha256.json').read_bytes())==pointer['manifest_sha256']
    for n,h in json.loads((source/'sha256.json').read_bytes()).items():assert sha((source/n).read_bytes())==h,n
    packet=next(p for p in json.loads((source/'packets.json').read_bytes())if p['candidate_seq']==seq)
    seen=PREP/'semantic-review-batches';seen.mkdir(exist_ok=True)
    assert not any(json.loads(p.read_bytes())['candidate_seq']==seq for p in seen.glob('*/review.json')),'Do not overwrite earlier independent labels'
    out=seen/str(time.time_ns());out.mkdir()
    row={'candidate_seq':seq,'candidate_event_sha256':packet['candidate_event_sha256'],'candidate_text_sha256':packet['candidate_text_sha256'],'source_packet_manifest_sha256':pointer['manifest_sha256'],'source_directory':str(source),'reviewer':'Codex single independent image/legal-source reviewer','review_scope':'Manual source/current-image/candidate review; checker/outcome fields not in exported packet. Legal histories include prior defense feedback; not fully blind. Status counts have been seen.','semantic_label':label,'native_action_error':native_error,'note':note,'checker_or_execution_joined':False,'time':time.time()}
    (out/'review.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'sha256.json').write_text(json.dumps({'review.json':sha((out/'review.json').read_bytes())},indent=2));print(json.dumps({'seq':seq,'label':label,'review_sha256':sha((out/'review.json').read_bytes())}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seq',type=int,required=True);p.add_argument('--label',choices=['no_definite_GUI_error','definite_GUI_error','unsupported_GUI_assertion','unresolved','pure_native_WAIT_excluded'],required=True);p.add_argument('--native-error',choices=['true','false','unknown'],default='unknown');p.add_argument('--note',required=True);a=p.parse_args();record(a.seq,a.label,{'true':True,'false':False,'unknown':None}[a.native_error],a.note)
