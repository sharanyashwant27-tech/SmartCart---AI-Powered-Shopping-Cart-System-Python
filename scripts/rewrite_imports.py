"""One-off import path rewriter for folder restructure."""

from pathlib import Path

root = Path(__file__).resolve().parents[1]

replacements = [
    ("from app.core.config import", "from app.config import"),
    ("from app.core.database import", "from app.database import"),
    ("from app.core.security import", "from app.utils.security import"),
    ("from app.core.exceptions import", "from app.utils.exceptions import"),
    ("from app.core.logging import", "from app.utils.logging import"),
    ("from app.core.enums import", "from app.utils.enums import"),
    ("from app.core.dependencies import", "from app.utils.dependencies import"),
    ("from app.core.rate_limit import", "from app.utils.rate_limit import"),
]

skip_parts = {".venv", "__pycache__", "scripts"}

updated = []
for path in root.rglob("*.py"):
    if any(part in skip_parts for part in path.parts):
        continue
    # Leave app/core/*.py as compatibility shims (rewritten separately)
    if path.parent.name == "core" and path.parent.parent.name == "app":
        continue
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        updated.append(str(path.relative_to(root)))

print(f"updated {len(updated)} files")
for u in updated:
    print(" -", u)
