import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
base=Path(__file__).resolve().parents[1]
files={path.name:base64.b64encode(path.read_bytes()).decode()for path in(base/'capacity-replay-launcher-01').glob('*.py')}
source=(base/'progress-preparation/stage_failed_capacity_source.py').read_text(encoding='utf8')
print(remote('SOURCE_FILES='+repr(files)+'\n'+source,timeout=120))
