"""SSH Python over stdin, no shell interpolation of code/data."""
import subprocess,sys
from pathlib import Path
def remote(code,timeout=90,host='3090'):
 p=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3','-'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')+'\n'+p.stdout.decode(errors='replace'))
 return p.stdout.decode()
if __name__=='__main__':print(remote(Path(sys.argv[1]).read_text(encoding='utf-8')))
