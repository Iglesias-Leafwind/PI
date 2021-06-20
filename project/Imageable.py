import sys
import time
import os
import subprocess
dir_path = os.path.dirname(os.path.realpath(__file__))

activate = os.path.join(dir_path, "venv/Scripts/python.exe")

initiate = os.path.join(dir_path, "initialize.py")

os.system('cmd /c ' + activate + ' ' + initiate)






