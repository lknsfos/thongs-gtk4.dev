# hooks/hook-gi.repository.Gtk.py
from PyInstaller.utils.hooks import collect_submodules
import os
import sys
import glob
import importlib

# Явно указываем PyInstaller включить все подмодули gi.repository
hiddenimports = collect_submodules('gi.repository')

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

    # Если gi уже импортирован — удалить и повторно импортировать после установки пути
    to_del = [k for k in list(sys.modules.keys()) if k == 'gi' or k.startswith('gi.')]
    if to_del:
        print(f"DEBUG: removing preloaded gi modules: {to_del}", file=sys.stderr)
    for k in to_del:
        sys.modules.pop(k, None)

    try:
        import gi
        # явные require_version перед импортом репозиториев
        try:
            gi.require_version("GLib", "2.0")
        except Exception:
            pass
        # импорт основных модулей чтобы инициализировать обвязки
        import gi.repository.GObject  # noqa: F401
        import gi.repository.GLib     # noqa: F401
        import gi.repository.Gtk      # noqa: F401
        print("DEBUG: gi re-imported after GI_TYPELIB_PATH set", file=sys.stderr)
    except Exception as e:
        print("DEBUG: failed to re-import gi:", e, file=sys.stderr)

_set_and_reload()