"""Send linked GET-only audit with failed script identities preserved."""
import base64
import json
from pathlib import Path
import sys
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
root = Path(__file__).resolve().parent
names = ['inspect_online_ready_remote.py', 'inspect_online_ready_remote_v2.py',
         'audit_online_ready_remote_v3.py', 'audit_online_ready_remote_v4.py']
sources = {name: base64.b64encode((root / name).read_bytes()).decode() for name in names}
code = 'AUDIT_SOURCES = ' + repr(sources) + '\n' + (root / names[-1]).read_text(encoding='utf8')
print(remote(code, timeout=90))
