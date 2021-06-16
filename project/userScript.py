import sys
import time
import os
import subprocess
dir_path = os.path.dirname(os.path.realpath(__file__))
#print(dir_path)
activate = os.path.join(dir_path, "venv/Scripts/activate")
#print(activate)
#subprocess.Popen(activate, shell=True)
initiate = os.path.join(dir_path, "initialize.py")
#print(initiate)
#subprocess.Popen("python "+ initiate, shell=True)
os.system('cmd /c ' + activate + " & python " + initiate)






