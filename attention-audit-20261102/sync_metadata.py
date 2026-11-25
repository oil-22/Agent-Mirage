"""Copy only campaign metadata and provenance, leaving NPZ tensors on 3090."""
import pathlib,subprocess,tarfile
R=pathlib.Path(__file__).parent
members=['campaign/plan.json','campaign/plan.sha256','button-campaign/plan.json','button-campaign/plan.sha256','button-campaign/mask-audit.json','source-campaign/plan.json','source-campaign/cpu-input-audit.json','source-campaign/variant-selection.json']
for prefix in ['','buttons-','source-']:
 for m in ['qwen27','qwen9','glm']:
  members += [prefix+m+'/'+n for n in ['status.json','runtime.json','results.json']]
  members += [prefix+m+'.log',prefix+m+'-preflight.log']
members += [m+'-controller.json' for m in ['qwen27','qwen9','glm']]+[m+'-extras-controller.json' for m in ['qwen27','qwen9','glm']]
archive=R/'metadata.tar.gz'
with archive.open('wb') as f:subprocess.run(['ssh','3090','tar -czf - -C /home/researcher/attention-20261102 '+' '.join(members)],stdout=f,check=True)
dest=R/'remote-metadata';dest.mkdir(exist_ok=True)
with tarfile.open(archive) as tar:tar.extractall(dest,filter='data')
print('copied',len(members),'metadata files')
