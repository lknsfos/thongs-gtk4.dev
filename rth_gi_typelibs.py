# rth_gi_typelibs.py
import os
import sys
import subprocess

# НАДЕЖНЫЙ СПОСОБ: Находим системный путь к typelib
try:
    # Этот путь является стандартным для большинства дистрибутивов Linux
    system_typelib_path = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
    if os.path.isdir(system_typelib_path):
        os.environ['GI_TYPELIB_PATH'] = system_typelib_path
except Exception as e:
    # На случай, если что-то пойдет не так
    print(f"FATAL: Could not set GI_TYPELIB_PATH. Error: {e}", file=sys.stderr)