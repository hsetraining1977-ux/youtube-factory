"""
Cross-platform font loader.
Finds a usable TrueType font on Windows, Linux, or Mac.
"""
from PIL import ImageFont

# Candidate paths in priority order (regular, bold)
_REGULAR_CANDIDATES = [
    "arial.ttf",                                                      # Windows (cwd/system)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", # Ubuntu/Debian
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",                 # Ubuntu fallback
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",                    # macOS
    "C:/Windows/Fonts/arial.ttf",                                      # Windows full path
]

_BOLD_CANDIDATES = [
    "arialbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

# Cache the first working path so we don't probe the filesystem every call
_resolved = {"regular": None, "bold": None}


def _resolve(candidates: list[str]) -> str | None:
    for path in candidates:
        try:
            ImageFont.truetype(path, 20)
            return path
        except Exception:
            continue
    return None


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return a usable font at the given size. Falls back to PIL default."""
    key = "bold" if bold else "regular"
    if _resolved[key] is None:
        _resolved[key] = _resolve(_BOLD_CANDIDATES if bold else _REGULAR_CANDIDATES)
    path = _resolved[key]
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()
