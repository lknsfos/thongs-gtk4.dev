import sys
import os

# --- САМЫЙ ВАЖНЫЙ ФИКС: ЯВНАЯ ИНИЦИАЛИЗАЦИЯ ПУТИ ---
# Этот код должен быть самым первым, до импорта чего-либо из GTK.
if hasattr(sys, '_MEIPASS'):
    # Указываем PyGObject искать typelib в папке, которую мы создали в .spec файле
    os.environ['GI_TYPELIB_PATH'] = os.path.join(sys._MEIPASS, 'gi', 'typelib')

from thongssh_gtk.app import main

if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)