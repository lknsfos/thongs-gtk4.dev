import os, sys, glob

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