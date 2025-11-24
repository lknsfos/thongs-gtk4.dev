import os
import sys
import glob

def _collapse_internal(path: str) -> str:
    return os.path.normpath(path.replace(os.path.join('_internal','_internal'), os.path.join('_internal')))

# Установить GI_TYPELIB_PATH если запущено из PyInstaller
if hasattr(sys, "_MEIPASS"):
    base = os.path.normpath(sys._MEIPASS)
    matches = glob.glob(os.path.join(base, "**", "gi", "typelib"), recursive=True)
    matches = [os.path.normpath(m) for m in matches if os.path.isdir(m)]
    if matches:
        candidate = _collapse_internal(matches[0])
        os.environ["GI_TYPELIB_PATH"] = candidate
        print(f"DEBUG: (entry) GI_TYPELIB_PATH set to: {candidate}", file=sys.stderr)

# Удаляем любые предзагруженные "gobject" и "gi" записи, чтобы gi.repository инициализировался корректно
for name in list(sys.modules.keys()):
    if name == "gobject" or name.startswith("gobject."):
        print(f"DEBUG: removing preloaded module: {name}", file=sys.stderr)
        sys.modules.pop(name, None)
for name in list(sys.modules.keys()):
    if name == "gi" or name.startswith("gi."):
        print(f"DEBUG: removing preloaded gi module: {name}", file=sys.stderr)
        sys.modules.pop(name, None)

from thongssh_gtk.app import main

if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)