# -*- mode: python ; coding: utf-8 -*-
import os
import glob

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import sys

block_cipher = None
script_file = 'run.py'

# Все ваши ресурсы (иконки, ui, шаблоны)
datas = []
datas.extend(collect_data_files('thongssh_gtk', subdir='resources'))
datas.extend(collect_data_files('thongssh_gtk', subdir='ui'))
# ✨ ПРАВИЛЬНОЕ МЕСТО для добавления gresource файла
datas.append(('thongssh_gtk/thongssh.gresource', '.'))

# Собираем system .typelib и добавляем в datas -> целевая папка 'gi/typelib' внутри dist
_typelib_dirs = [
    '/usr/lib/girepository-1.0',
    '/usr/lib64/girepository-1.0',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0',
    '/usr/local/lib/girepository-1.0',
]
_typelib_datas = []
for _d in _typelib_dirs:
    if os.path.isdir(_d):
        for _f in glob.glob(os.path.join(_d, '*.typelib')):
            # целевая папка внутри dist: gi/typelib
            _typelib_datas.append((_f, os.path.join('gi', 'typelib')))

# объединяем с существующими datas (если есть)
datas = (globals().get('datas') or []) + _typelib_datas

a = Analysis(
    [script_file],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=['./hooks'],
    runtime_hooks=['rth_gi_force_reload.py', 'rth_gi_typelibs.py'],
    excludes=[],
    noarchive=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='thongs-gtk4',
    debug=False,
    strip=False,
    upx=True,
    console=True
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='thongs-gtk4'
)

if hasattr(sys, '_MEIPASS'):
    typelib_dir = os.path.join(sys._MEIPASS, 'gi', 'typelib')
    os.environ['GI_TYPELIB_PATH'] = typelib_dir
    print(f"DEBUG: GI_TYPELIB_PATH set to: {typelib_dir}", file=sys.stderr)
