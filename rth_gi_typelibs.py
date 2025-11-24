# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import os
import sys
import glob

def _set_typelib_path():
    if not hasattr(sys, '_MEIPASS'):
        return
    base = os.path.normpath(sys._MEIPASS)

    # ищем все каталоги gi/typelib внутри распакованного пакета
    matches = glob.glob(os.path.join(base, '**', 'gi', 'typelib'), recursive=True)
    matches = [os.path.normpath(m) for m in matches if os.path.isdir(m)]

    # fallback: также проверить прямой путь
    if not matches:
        direct = os.path.normpath(os.path.join(base, '_internal', 'gi', 'typelib'))
        if os.path.isdir(direct):
            matches = [direct]
    if not matches:
        print("DEBUG: No gi/typelib directory found inside sys._MEIPASS", file=sys.stderr)
        return

    candidate = matches[0]
    # дополнительная отладка: показать, какие .typelib внутри candidate
    try:
        files = sorted(os.listdir(candidate))
    except Exception:
        files = []
    print(f"DEBUG: GI_TYPELIB_PATH set to: {candidate}", file=sys.stderr)
    print(f"DEBUG: typelibs in that dir: {files[:200]}", file=sys.stderr)
    os.environ['GI_TYPELIB_PATH'] = candidate

_set_typelib_path()