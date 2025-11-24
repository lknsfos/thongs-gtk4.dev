# rth_gi_typelibs.py
import os
import sys

# Этот хук выполняется до запуска основного скрипта.
# Его задача - установить переменные окружения, чтобы PyGObject нашел свои библиотеки.

# 1. Путь к typelib файлам, которые PyInstaller упаковал.
bundled_typelib_path = os.path.join(sys._MEIPASS, 'gi', 'typelib')

# 2. Стандартные системные пути, где могут лежать typelib файлы.
system_typelib_paths = [
    '/usr/lib/x86_64-linux-gnu/girepository-1.0',
    '/usr/lib/girepository-1.0',
    '/usr/local/lib/girepository-1.0',
]

# 3. Формируем новый GI_TYPELIB_PATH.
# Сначала добавляем упакованный путь, затем все существующие системные пути.
new_path = [bundled_typelib_path]
for path in system_typelib_paths:
    if os.path.isdir(path):
        new_path.append(path)

# 4. Устанавливаем переменную окружения.
os.environ['GI_TYPELIB_PATH'] = os.pathsep.join(new_path)

# Для отладки: выводим установленный путь в консоль при запуске.
print(f"DEBUG: GI_TYPELIB_PATH set to: {os.environ['GI_TYPELIB_PATH']}", file=sys.stderr)