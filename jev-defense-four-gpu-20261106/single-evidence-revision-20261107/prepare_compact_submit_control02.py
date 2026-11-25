"""Create a new reviewed submission control, never invoke it here."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'submit_new_four_gpu_preflight_once.py').read_text(encoding='utf8')
s=s.replace('import time\n','import time\nimport sys\n')
s=s.replace("ROOT/'gpu-preflight-launcher-01/frozen-gpu-four-linked02-01'","ROOT/'compact-launcher-02/frozen-compact-gpu-02'")
s=s.replace('source-first-four-root-review-01','source-first-compact-four-peer-notes-02')
s=s.replace('actual-four-GPU-submission-01','actual-compact-four-GPU-submission-02')
s=s.replace('runtime-preparation/single-jev-9b-preflight-01','runtime-preparation/single-jev-9b-compact-preflight-02')
s=s.replace('neutral-image-four-preflight-01.json','neutral-image-compact-four-preflight-02.json')
s=s.replace("=='94e45e2d07c2b22e3979645f0a633259e7a0a60dfc89837014e39e7a13d57b44'","==sys.argv[1]")
s=s.replace('fbcff9cdc43380775f496d9a7e5da2fbd0a2a8a89549604544fd82e25995ae79','688f27b2fa0f28b31f3e3cf5632efe1316f3dcaee364407478fcf94d078485c1')
s=s.replace('concrete_new_four_first_attempts_reviewed','concrete_new_compact_four_sources_reviewed')
assert 'single-jev-9b-preflight-01'not in s
assert 'frozen-gpu-four-linked02-01'not in s
assert 'neutral-image-four-preflight-01.json'not in s
with(R/'submit_compact_four_gpu_once02.py').open('x',encoding='utf8',newline='\n')as f:f.write(s)
for old,new in [('inspect_new_four_gpu_preflight.py','inspect_compact_four_gpu02.py'),('collect_new_four_gpu_results.py','collect_compact_four_gpu02.py')]:
    text=(R/old).read_text(encoding='utf8')
    text=text.replace('gpu-four-first-attempts-01','gpu-compact-four-first-attempts-02')
    text=text.replace('single-jev-9b-preflight-01','single-jev-9b-compact-preflight-02')
    text=text.replace('gpu-four-terminal-collection-01','gpu-compact-four-terminal-collection-02')
    text=text.replace('gpu-progress-evidence','gpu-compact-progress-evidence-02')
    with(R/new).open('x',encoding='utf8',newline='\n')as f:f.write(text)
print('Prepared new submission, inspector and collector; no execution.')
