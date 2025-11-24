# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
# --- НАДЁЖНЫЙ СПОСОБ: Установка путей до инициализации Gtk ---
# Этот хук выполняется до основного скрипта.
def _set_typelib_path():
    if not hasattr(sys, '_MEIPASS'):
        return
    # ожидаем, что datas положили в _internal/gi/typelib внутри dist
    # но не добавляем '_internal' дважды — нормализуем путь
    candidate = os.path.join(sys._MEIPASS, '_internal', 'gi', 'typelib')
    candidate = os.path.normpath(candidate)
    if os.path.isdir(candidate):
        os.environ['GI_TYPELIB_PATH'] = candidate
        print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {candidate}", file=sys.stderr)

_set_typelib_path()