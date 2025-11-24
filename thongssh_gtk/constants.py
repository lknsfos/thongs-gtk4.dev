import sys
import os

APP_ID = "com.example.thongssh"

def resource_path(relative_path, in_module=True):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    - in_module=True: path is relative to the thongssh_gtk module folder.
    - in_module=False: path is relative to the bundle's root (_MEIPASS).
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if hasattr(sys, '_MEIPASS'):
        if in_module:
            return os.path.join(sys._MEIPASS, 'thongssh_gtk', relative_path)
        return os.path.join(sys._MEIPASS, relative_path)

    # In development, the path is relative to the project root,
    # assuming constants.py is in thongssh_gtk/
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, 'thongssh_gtk', relative_path)

# --- КОЛОНКИ TreeStore ---
# (Имя, Тип, Иконка, Объект данных (config/node))
(
    COL_NAME,
    COL_TYPE,
    COL_ICON,
    COL_DATA
) = range(4)
# -------------------------