"""Source/CPU only; never submits holder command."""
import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
here=Path(__file__).resolve().parent/'submit-control-linked01'
sources={p.name:base64.b64encode(p.read_bytes()).decode()for p in here.glob('*.py')}
print(remote('REPAIR_SOURCES='+repr(sources)+'\n'+(here/'preserve_and_prepare_remote.py').read_text(encoding='utf8'),timeout=180,host='3090'))
