# rth_gi_typelibs.py
import os
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import glob

def _find_typelib_dir(base):
    cand = glob.glob(os.path.join(base, "**", "gi", "typelib"), recursive=True)
    for p in sorted(set(os.path.normpath(m) for m in cand)):
        try:
            files = [f for f in os.listdir(p) if f.endswith('.typelib')]
        except Exception:
            files = []
        if files:
            return p
    for trial in (os.path.join(base, '_internal', 'gi', 'typelib'),
                  os.path.join(base, 'gi', 'typelib')):
        trial = os.path.normpath(trial)
        if os.path.isdir(trial):
            try:
                files = [f for f in os.listdir(trial) if f.endswith('.typelib')]
            except Exception:
                files = []
            if files:
                return trial
    return None

def _set_typelib_path():
    if not hasattr(sys, '_MEIPASS'):
        return
    base = os.path.normpath(sys._MEIPASS)
    typedir = _find_typelib_dir(base)
    if not typedir:
        print("DEBUG: No gi/typelib directory with .typelib files found inside sys._MEIPASS", file=sys.stderr)
        return
    typedir = os.path.normpath(typedir)
    # collapse accidental double _internal segments
    typedir = typedir.replace(os.path.join('_internal', '_internal'), os.path.join('_internal'))
    os.environ['GI_TYPELIB_PATH'] = typedir
    print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {typedir}", file=sys.stderr)
    try:
        print(f"DEBUG: typelibs: {sorted([f for f in os.listdir(typedir) if f.endswith('.typelib')])[:300]}", file=sys.stderr)
    except Exception:
        pass

_set_typelib_path()