import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
base=Path(__file__).resolve().parent
names=['preserve_failed_service_remote.py','inspect_failed_judge_remote.py']
sources={name:base64.b64encode((base/name).read_bytes()).decode()for name in names}
helper=base64.b64encode((base/'progress_remote.py').read_bytes()).decode()
code='PRESERVATION_SOURCES='+repr(sources)+'\nPROGRESS_HELPER='+repr(helper)+'\n'+(base/names[0]).read_text(encoding='utf8')
print(remote(code,timeout=240))
