"""Snapshot default makes no health calls; root alone authorizes --health-once."""
import argparse
import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
p=argparse.ArgumentParser();p.add_argument('--health-once',action='store_true');a=p.parse_args()
here=Path(__file__).resolve().parent
source=here/'audit_three_ready_remote.py'
sources={p.name:base64.b64encode(p.read_bytes()).decode()for p in here.glob('*.py')}
prefix='ALLOW_HEALTH='+repr(a.health_once)+'\nAUDITOR_SOURCES='+repr(sources)+'\n'
print(remote(prefix+source.read_text(encoding='utf8'),timeout=180,host='3090'))
