import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
path=Path(__file__).with_name('audit_single_capacity_terminal_remote.py')
sources={path.name:base64.b64encode(path.read_bytes()).decode()}
print(remote('AUDITOR_SOURCES='+repr(sources)+'\n'+path.read_text(encoding='utf8'),timeout=180))
