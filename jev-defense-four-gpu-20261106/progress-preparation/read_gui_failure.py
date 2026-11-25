from pathlib import Path
import sys
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
print(remote(Path(__file__).with_name('read_gui_failure_remote.py').read_text(encoding='utf8'), host='4090'))
