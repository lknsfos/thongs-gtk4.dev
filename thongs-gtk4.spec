# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import glob

block_cipher = None
script_file = 'run.py'

# Все ваши ресурсы (иконки, ui, шаблоны)
datas = []
datas.extend(collect_data_files('thongssh_gtk', subdir='resources'))
datas.extend(collect_data_files('thongssh_gtk', subdir='ui'))
# ✨ ПРАВИЛЬНОЕ МЕСТО для добавления gresource файла
datas.append(('thongssh_gtk/thongssh.gresource', '.'))

# --- САМЫЙ ТУПОЙ, НО НАДЁЖНЫЙ СПОСОБ ---
# Копируем все системные typelib в корень бандла.
typelib_path = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
if os.path.isdir(typelib_path):
    datas.extend([(f, '.') for f in glob.glob(os.path.join(typelib_path, '*.typelib'))])

a = Analysis(
    [script_file],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[], # Убираем хуки, они не работают.
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
