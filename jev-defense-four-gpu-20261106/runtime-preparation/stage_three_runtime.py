"""Upload new sources/prepare private token and spec; never finalize or launch."""
import base64
from pathlib import Path
import sys

sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

here=Path(__file__).resolve().parent
source=here/'gui-three-linked-02'
sources={p.name:base64.b64encode(p.read_bytes()).decode()for p in source.glob('*.py')}
plan=here.parent/'policy-preparation/image-observer-policy/gui-migration-three-01/cpu-preparation/1793984609630698800/plan.proposed.json'
prefix='ONLINE_SOURCES='+repr(sources)+'\nPLAN_SOURCE='+repr(base64.b64encode(plan.read_bytes()).decode())+'\n'
print(remote(prefix+(source/'prepare_sources_remote.py').read_text(encoding='utf8'),timeout=180,host='3090'))
