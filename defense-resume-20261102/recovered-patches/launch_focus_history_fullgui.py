"""Once-only new fullGUI launch with the measured repair version and human instruction."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'launch_scoped_fullgui.py').read_text(encoding='utf-8')
source=source.replace("PREP=BASE/'scoped-observability-development'", "PREP=BASE/'focus-history-fullgui-development'")
source=source.replace('scoped-fullgui-active-20261028.json','focus-history-fullgui-active-20261029.json')
source=source.replace("'scoped-joint-stale-fullgui-'+", "'focus-history-joint-stale-fullgui-'+")
old="held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()];assert len(held)>=len(locks)"
new="""held=[]
for f in (proc/'fdinfo').iterdir():
 try:
  info=f.read_text()
  if 'FLOCK' in info:held.append({'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':info})
 except FileNotFoundError:pass
assert all(any(x['target']==f.name for x in held)for f in locks),held"""
assert source.count(old)==1
source=source.replace(old,new)
exec(compile(source,str(BASE/'launch_focus_history_fullgui.generated.py'),'exec'))
