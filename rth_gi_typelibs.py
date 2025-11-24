# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import os, sys, glob

# --- НАДЁЖНЫЙ СПОСОБ: Установка путей до инициализации Gtk ---
# Этот хук выполняется до основного скрипта.
def _set_typelib_path():
    if not hasattr(sys, "_MEIPASS"):
        return
    base = sys._MEIPASS
    # ищем любую папку .../gi/typelib внутри распакованного пакета
    matches = glob.glob(os.path.join(base, "**", "gi", "typelib"), recursive=True)
    matches = [m for m in matches if os.path.isdir(m)]
    # fallback на старые варианты
    if not matches:
        fallback = os.path.normpath(os.path.join(base, "_internal", "gi", "typelib"))
        if os.path.isdir(fallback):
            matches = [fallback]
    if not matches:
        # ничего не нашли — оставляем как есть (debug)
        print("DEBUG: No gi/typelib directory found inside sys._MEIPASS", file=sys.stderr)
        return
    candidate = os.path.normpath(matches[0])
    os.environ["GI_TYPELIB_PATH"] = candidate
    print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {candidate}", file=sys.stderr)

_set_typelib_path()