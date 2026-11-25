"""Linked private-only token-cache repair; original failed source is immutable."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
OLD=HERE/'isolated-runtime-source'
NEW=HERE/'isolated-runtime-source-linked02'
shutil.copytree(OLD,NEW,ignore=shutil.ignore_patterns('__pycache__','*.pyc','source-seal.json'))
source=NEW/'grammar-vendor/lmformatenforcer/tokenenforcer.py'
text=source.read_text(encoding='utf8')
needle="characters_to_explore = characters_to_explore.intersection(['\"'])"
assert text.count(needle)==1
replacement="characters_to_explore = characters_to_explore.intersection(['\"', '\\\\'])"
text=text.replace(needle,
 '# Private byte-token compatibility: incomplete JSON escape prefixes are\n'
 '            # excluded by the freetext cache; traverse backslash branches with\n'
 '            # the unchanged character parser instead of dropping legal tokens.\n'
 '            '+replacement)
source.write_text(text,encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
identity=NEW/'auxiliary-grammar-identity.json'
ref=json.loads(identity.read_bytes());root=NEW/'grammar-vendor/lmformatenforcer'
ref['private_files']={p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()}
identity.write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with(NEW/'source-seal.json').open('x',encoding='utf8')as f:
 json.dump({p.relative_to(NEW).as_posix():sha(p)for p in NEW.rglob('*')if p.is_file()and p.name!='source-seal.json'},f,indent=2);f.write('\n')
with(HERE/'linked02-preparation.json').open('x',encoding='utf8')as f:
 json.dump({'time':time.time(),'original_source':str(OLD),'original_seal_sha256':sha(OLD/'source-seal.json'),
 'linked_source':str(NEW),'linked_seal_sha256':sha(NEW/'source-seal.json'),
 'failure_diagnostic':str(HERE/'integration-escape-failure-preservation-01/linked-diagnostic.json'),
 'failure_diagnostic_sha256':sha(HERE/'integration-escape-failure-preservation-01/linked-diagnostic.json'),
 'change':'Private TokenEnforcer explores JSON backslash-prefix tokens using its existing character parser when omitted by the fast freetext cache.',
 'canonical_main_modified':False,'new_model_GUI_calls':0,'semantic_accuracy_or_efficacy_established':False,
 'tradeoff':'May add auxiliary mask-computation latency. No new truth, corrected text, action, image resizing, history truncation or final-validator relaxation.'},f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'source':str(NEW),'seal_sha256':sha(NEW/'source-seal.json'),'model_GUI_calls':0}))
