# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
script_file = 'run.py'

# Все ваши ресурсы (иконки, ui, шаблоны)
datas = collect_data_files('thongssh_gtk', subdir='resources')
datas += collect_data_files('thongssh_gtk', subdir='icons')
datas += collect_data_files('thongssh_gtk', subdir='ui')

# Собираем GI typelib вручную
typelibs = [
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/Gtk-4.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/Gdk-4.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/GdkPixbuf-2.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/GLib-2.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/GObject-2.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/Pango-1.0.typelib',
    '/usr/lib/x86_64-linux-gnu/girepository-1.0/Adw-1.typelib',
]

for t in typelibs:
    datas.append((t, os.path.join('usr', 'lib', 'girepository-1.0')))

a = Analysis(
    [script_file],
    pathex=[os.path.abspath('.')],
    binaries=[],
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
