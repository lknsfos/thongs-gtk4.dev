# hooks/hook-gi.repository.Gtk.py
from PyInstaller.utils.hooks import collect_submodules

# Явно указываем PyInstaller включить все подмодули gi.repository
hiddenimports = collect_submodules('gi.repository')