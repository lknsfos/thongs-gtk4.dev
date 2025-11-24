# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
# --- НАДЁЖНЫЙ СПОСОБ: Установка путей до инициализации Gtk ---
# Этот хук выполняется до основного скрипта.
if hasattr(sys, '_MEIPASS'):
    # Устанавливаем путь поиска typelib ЯВНО на каталог внутри пакета.
    os.environ['GI_TYPELIB_PATH'] = os.path.join(sys._MEIPASS, 'gi', 'typelib')
    # Для отладки:
    print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {os.environ['GI_TYPELIB_PATH']}", file=sys.stderr)