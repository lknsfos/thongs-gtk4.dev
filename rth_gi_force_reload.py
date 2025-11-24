import os
import sys
import glob
import importlib

def _find_typelib_dir(base):
    cand = glob.glob(os.path.join(base, "**", "typelib"), recursive=True)
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

def _set_and_reload():
    if not hasattr(sys, '_MEIPASS'):
        return
    base = os.path.normpath(sys._MEIPASS)
    typedir = _find_typelib_dir(base)
    if not typedir:
        print("DEBUG: No gi/typelib directory with .typelib files found inside sys._MEIPASS", file=sys.stderr)
        return
    typedir = os.path.normpath(typedir)
    os.environ['GI_TYPELIB_PATH'] = typedir
    print(f"DEBUG: GI_TYPELIB_PATH explicitly set to: {typedir}", file=sys.stderr)
    try:
        print(f"DEBUG: typelibs: {sorted([f for f in os.listdir(typedir) if f.endswith('.typelib')])[:200]}", file=sys.stderr)
    except Exception:
        pass

    # remove any preloaded gi.* and any gobject* entries BEFORE re-import
    to_del = [k for k in list(sys.modules.keys()) if k == 'gi' or k.startswith('gi.') or k == 'gobject' or k.startswith('gobject.')]
    if to_del:
        print(f"DEBUG: removing preloaded modules: {to_del}", file=sys.stderr)
    for k in to_del:
        sys.modules.pop(k, None)

    # ensure no stray file named 'gobject' on sys.path shadows gi (diagnostics)
    for p in sys.path:
        try:
            for cand in ('gobject.py', 'gobject', 'gobject.so', 'gobject.pyd'):
                fp = os.path.join(p, cand)
                if os.path.exists(fp):
                    print(f"DEBUG: found possible shadowing file: {fp}", file=sys.stderr)
        except Exception:
            pass

    # now import gi and core repositories
    try:
        import gi
        gi.require_version("GLib", "2.0")
        import gi.repository.GObject  # noqa: F401
        import gi.repository.GLib     # noqa: F401
        gi.require_version("Gtk", "4.0")
        import gi.repository.Gtk      # noqa: F401
        print("DEBUG: gi re-imported after GI_TYPELIB_PATH set", file=sys.stderr)
    except Exception as e:
        print("DEBUG: failed to re-import gi:", e, file=sys.stderr)

_set_and_reload()