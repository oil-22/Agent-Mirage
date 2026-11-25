"""Linked public rejection-only export; preserve the completed original export."""
import hashlib
import json
import sys
from pathlib import Path

from inspect_three_join_source import CODE
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

if __name__ == '__main__':
    code=CODE.replace("if any(term in kind for term in ['accepted','rejected','executed','candidate','recapture','regenerat']):", "if kind in {'verdict','state_invalidated','verifier_format_failure','decision_blocked','history_report_crosscheck'}:")
    assert code!=CODE
    out=Path(__file__).parent/'postlabel-join-source-linked02'
    out.mkdir(exist_ok=False)
    data=json.loads(remote(code,timeout=60,host='4090'))
    with(out/'public-controller-rejection-source.json').open('x',encoding='utf8')as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'remote-source.py').write_text(code,encoding='utf8')
    mapping={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()}
    with(out/'seal.json').open('x',encoding='utf8')as f:json.dump(mapping,f,indent=2)
    print(json.dumps({'out':str(out),'source_sha256':data['source_sha256'],'event_count':data['event_count'],'selected_count':len(data['selected_public_rows']),'seal_sha256':hashlib.sha256((out/'seal.json').read_bytes()).hexdigest()}))
