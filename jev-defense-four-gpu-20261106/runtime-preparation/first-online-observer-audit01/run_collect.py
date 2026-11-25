import base64,json,sys
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
here=Path(__file__).resolve().parent
sources={p.name:base64.b64encode(p.read_bytes()).decode()for p in here.glob('*.py')}
code='AUDIT_SOURCES='+repr(sources)+'\n'+(here/'collect_service_remote.py').read_text(encoding='utf8')
print(remote(code,timeout=180,host='3090'))
