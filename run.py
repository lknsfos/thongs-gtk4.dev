import sys, os, traceback

# Диагностика: какие модули с "gobject" уже загружены и откуда они
for name, mod in list(sys.modules.items()):
    if name == 'gobject' or 'gobject' in name:
        print(f"DEBUG-MODULE: {name} -> {getattr(mod, '__file__', None)}", file=sys.stderr)

# Диагностика: показать sys.path и первые 40 записей в окружении, полезно для поиска site-packages
print("DEBUG-SYSPATH:", file=sys.stderr)
for p in sys.path:
    print("  ", p, file=sys.stderr)
print("DEBUG-ENV GI_TYPELIB_PATH:", os.environ.get('GI_TYPELIB_PATH'), file=sys.stderr)

if hasattr(sys, "_MEIPASS"):
    base = os.path.normpath(sys._MEIPASS)
    matches = glob.glob(os.path.join(base, "**", "gi", "typelib"), recursive=True)
    matches = [os.path.normpath(m) for m in matches if os.path.isdir(m)]
    if matches:
        candidate = matches[0]
        # нормализация на случай двойного _internal
        candidate = candidate.replace(os.path.join('_internal','_internal'), os.path.join('_internal'))
        candidate = os.path.normpath(candidate)
        os.environ["GI_TYPELIB_PATH"] = candidate
        print(f"DEBUG: (entry) GI_TYPELIB_PATH set to: {candidate}", file=sys.stderr)

from thongssh_gtk.app import main

if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)