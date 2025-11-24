# rth_gi_typelibs.py
import os
import sys

# добавляем путь с typelib в GI_TYPELIB_PATH
meipass = getattr(sys, '_MEIPASS', os.path.abspath('.'))
typelib_path = os.path.join(meipass, 'usr', 'lib', 'girepository-1.0')
os.environ['GI_TYPELIB_PATH'] = typelib_path + ':' + os.environ.get('GI_TYPELIB_PATH', '')