# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import glob
import sys

block_cipher = None
script_file = 'run.py'

# Все ваши ресурсы (иконки, ui, шаблоны)
datas = []
datas.extend(collect_data_files('thongssh_gtk', subdir='resources'))
datas.extend(collect_data_files('thongssh_gtk', subdir='ui'))
# ✨ ПРАВИЛЬНОЕ МЕСТО для добавления gresource файла
datas.append(('thongssh_gtk/thongssh.gresource', '.'))

# --- САМЫЙ НАДЁЖНЫЙ СПОСОБ: ЯВНОЕ КОПИРОВАНИЕ СИСТЕМНЫХ TYPELIB ---
# Находим все .typelib файлы в системном каталоге и копируем их в папку gi/typelib внутри сборки.
typelib_src_dirs = [
    '/usr/lib/girepository-1.0',
    '/usr/lib64/girepository-1.0',
    '/usr/local/lib/girepository-1.0',
]
typelib_datas = []
for d in typelib_src_dirs:
    if os.path.isdir(d):
        for f in glob.glob(os.path.join(d, '*.typelib')):
            # положить в _internal/gi/typelib внутри dist
            typelib_datas.append((f, os.path.join('_internal', 'gi', 'typelib')))

# append to existing datas variable used by Analysis
datas = datas + typelib_datas

a = Analysis(
    [script_file],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=['./hooks'],
    runtime_hooks=['rth_gi_typelibs.py'],
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
