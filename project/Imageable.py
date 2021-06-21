import sys
import time
import os
import subprocess
import pathlib
dir_path = pathlib.Path().absolute()

activate = os.path.join(dir_path, "venv/Scripts/python.exe")

initiate = os.path.join(dir_path, "initialize.py")

os.system('cmd /c ' + activate + ' ' + initiate)






