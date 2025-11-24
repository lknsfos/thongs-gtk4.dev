# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
# --- НАДЁЖНЫЙ СПОСОБ: Установка путей до инициализации Gtk ---
# Этот хук выполняется до основного скрипта.
def _set_typelib_path():
    # при обычном запуске ничего менять не нужно
    if hasattr(sys, '_MEIPASS'):
        candidate = os.path.join(sys._MEIPASS, '_internal', 'gi', 'typelib')
        if os.path.isdir(candidate):
            os.environ['GI_TYPELIB_PATH'] = candidate
            # отладочный вывод в stderr (можно удалить после теста)
            print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {candidate}", file=sys.stderr)

_set_typelib_path()