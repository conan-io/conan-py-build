"""MkDocs hook: generate llms-full.txt during build."""
import re
from pathlib import Path


# Strip Material-specific syntax that adds noise for LLMs
_STRIP = [
    re.compile(r'^={3} ".*?"$', re.MULTILINE),  # tabbed: === "Tab"
    re.compile(r'^={3}$', re.MULTILINE),          # tabbed: ===
]


def _clean(text: str) -> str:
    for pattern in _STRIP:
        text = pattern.sub("", text)
    # Collapse runs of 3+ blank lines down to two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pages_from_nav(nav) -> list[str]:
    """Recursively extract page paths from the MkDocs nav structure."""
    pages = []
    for entry in nav:
        for value in entry.values():
            if isinstance(value, str):
                pages.append(value)
            elif isinstance(value, list):
                pages.extend(_pages_from_nav(value))
    return pages


def on_post_build(config):
    docs_dir = Path(config["docs_dir"])
    site_dir = Path(config["site_dir"])

    parts = []
    for page in _pages_from_nav(config["nav"]):
        path = docs_dir / page
        if path.suffix != ".md" or not path.exists():
            continue
        parts.append(_clean(path.read_text(encoding="utf-8")))

    output = "\n\n---\n\n".join(parts) + "\n"
    (site_dir / "llms-full.txt").write_text(output, encoding="utf-8")
