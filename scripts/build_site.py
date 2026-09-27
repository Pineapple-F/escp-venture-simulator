"""Publish only the current UI; never expose runtime data or user saves."""
from pathlib import Path
import shutil


def build():
    root = Path(__file__).resolve().parents[1]
    source = root / 'market-simulator/web'
    target = root / 'public'
    target.mkdir(exist_ok=True)
    if target.is_symlink() or target.resolve().parent != root.resolve():
        raise RuntimeError('Unexpected public directory')
    for entry in target.iterdir():
        if entry.is_symlink() or entry.is_file():
            entry.unlink()
        else:
            shutil.rmtree(entry)
    for entry in source.iterdir():
        if entry.is_file() and entry.suffix in ('.html', '.css', '.js', '.svg', '.png', '.ico'):
            shutil.copy2(entry, target / entry.name)
    (target / '_headers').write_text(
        '/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: same-origin\n', encoding='utf-8')
    assert (target / 'index.html').is_file() and (target / 'founder.html').is_file()
    print(f'Built {len(list(target.iterdir()))} frontend assets from market-simulator/web')


if __name__ == '__main__':
    build()
