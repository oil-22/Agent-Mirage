"""Linked CPU-only metadata projection. First attempt incorrectly assumed every candidate was text."""
from pathlib import Path
import hashlib,json
p=Path(__file__).parent
old=p/'prepare_judge_semantic_reading.py'
source=old.read_text(encoding='utf-8')
source=source.replace("dest=root/'judge-semantic-reading-01'","dest=root/'judge-semantic-reading-linked02'")
source=source.replace("ch=h(cand.encode()) if cand is not None else None","ch=h(json.dumps(cand,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()) if cand is not None else None")
assert 'cand.encode()' not in source
failure={'scope':'CPU-only derived audit metadata failure','original_source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
 'error':"AttributeError: dict candidate has no encode",'original_failed_empty_root':'judge-semantic-reading-01',
 'fix':'Canonical JSON hash supports both structured and string native candidates. Original values unchanged.',
 'new_model_GUI_scorer_calls':0,'original_experiment_changed':False}
failure_path=p/'judge-semantic-reading-01-failure.json'
assert not failure_path.exists();failure_path.write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
exec(compile(source,str(Path(__file__)), 'exec'))
