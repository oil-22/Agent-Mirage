import pathlib,subprocess,json,time
root=pathlib.Path(__file__).parent
with (root/'transfer.log').open('w',encoding='utf-8') as log:
 subprocess.run(['ssh','3090','mkdir -p /home/researcher/attention-20261102'],check=True,stdout=log,stderr=log)
 src=subprocess.Popen(['ssh','4090','tar -cf - -C /data/researcher/attention-audit-20261102 campaign'],stdout=subprocess.PIPE,stderr=log)
 dst=subprocess.Popen(['ssh','3090','tar -xf - -C /home/researcher/attention-20261102'],stdin=src.stdout,stdout=log,stderr=log)
 src.stdout.close();dr=dst.wait();sr=src.wait()
 assert dr==sr==0,(dr,sr)
print('campaign transferred')
