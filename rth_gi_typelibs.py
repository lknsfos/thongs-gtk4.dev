# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import os
import sys
import glob

def _collapse_internal(path: str) -> str:
    # убирает повторяющиеся "_internal/_internal"
    part = os.path.join('_internal', '_internal')
    while part in path:
        path = path.replace(part, os.path.join('_internal'))
    return os.path.normpath(path)

def _set_typelib_path():
    if not hasattr(sys, '_MEIPASS'):
        return
    base = os.path.normpath(sys._MEIPASS)
    matches = glob.glob(os.path.join(base, '**', 'gi', 'typelib'), recursive=True)
    matches = [os.path.normpath(m) for m in matches if os.path.isdir(m)]
    if not matches:
        fallback = os.path.normpath(os.path.join(base, '_internal', 'gi', 'typelib'))
        if os.path.isdir(fallback):
            matches = [fallback]
    if not matches:
        print("DEBUG: No gi/typelib directory found inside sys._MEIPASS", file=sys.stderr)
        return
    candidate = _collapse_internal(matches[0])
    os.environ['GI_TYPELIB_PATH'] = candidate
    try:
        files = sorted(os.listdir(candidate))
    except Exception:
        files = []
    print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {candidate}", file=sys.stderr)
    print(f"DEBUG: typelibs in that dir: {files[:200]}", file=sys.stderr)

_set_typelib_path()