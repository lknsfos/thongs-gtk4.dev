# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None
script_file = 'run.py'

# Все ваши ресурсы (иконки, ui, шаблоны)
datas = []
datas.extend(collect_data_files('thongssh_gtk', subdir='resources'))
datas.extend(collect_data_files('thongssh_gtk', subdir='ui'))
# ✨ ПРАВИЛЬНОЕ МЕСТО для добавления gresource файла
datas.append(('thongssh_gtk/thongssh.gresource', '.'))

# ✨ Автоматический сбор всех typelib файлов
datas.extend(collect_data_files('gi', subdir='typelib'))

a = Analysis(
    [script_file],
    pathex=[os.path.abspath('.')],
    binaries=collect_dynamic_libs('gi'), # ✨ Автоматический сбор библиотек gi
    datas=datas,
    hiddenimports=[],
    hookspath=[],
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
