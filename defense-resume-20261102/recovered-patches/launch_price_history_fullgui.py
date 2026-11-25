"""One authorized NEW trajectory; old active/terminal receipts never touched."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
s=(BASE/'launch_scoped_fullgui.py').read_text(encoding='utf-8')
s=s.replace("PREP=BASE/'scoped-observability-development'","PREP=BASE/'price-history-fullgui-development'")
s=s.replace('scoped-fullgui-active-20261028.json','price-history-fullgui-active-20261029.json')
s=s.replace("'scoped-joint-stale-fullgui-'+","'price-history-joint-stale-fullgui-'+")
old="held=[{'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':f.read_text()}for f in(proc/'fdinfo').iterdir()if'FLOCK'in f.read_text()];assert len(held)>=len(locks)"
new="""held=[]
for f in (proc/'fdinfo').iterdir():
 try:
  info=f.read_text()
  if 'FLOCK' in info:held.append({'target':os.readlink(str(proc/'fd'/f.name)),'fdinfo':info})
 except FileNotFoundError:pass
assert all(any(x['target']==f.name for x in held)for f in locks),held"""
assert s.count(old)==1;s=s.replace(old,new)
exec(compile(s,str(BASE/'launch_price_history_fullgui.generated.py'),'exec'))
