import re
from pathlib import Path
import shutil

ROOT = Path('.').resolve()
py_files = list(ROOT.rglob('*.py'))

patterns = [
    (re.compile(r'^\s*import\s+gobject\b', re.M), "from gi.repository import GObject"),
    (re.compile(r'^\s*from\s+gobject\s+import\s+', re.M), lambda m: m.group(0).replace('from gobject import ', 'from gi.repository.GObject import ')),
    (re.compile(r'\bgobject\.'), 'GObject.')
]

def process_file(p: Path):
    text = p.read_text(encoding='utf-8')
    orig = text
    for pat, repl in patterns:
        if isinstance(repl, str):
            text = pat.sub(repl, text)
        else:
            text = pat.sub(repl, text)
    if text != orig:
        bak = p.with_suffix(p.suffix + '.bak')
        shutil.copy2(p, bak)
        p.write_text(text, encoding='utf-8')
        print(f'Patched: {p} (backup -> {bak})')

for f in py_files:
    process_file(f)
print('Done.')