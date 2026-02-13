"""Shared utilities: colors, output formatting."""

import io
import os
import sys

# Force UTF-8 output on Windows to handle box/progress chars
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
}

NO_COLOR = os.environ.get("NO_COLOR") is not None


def c(text: str, color: str) -> str:
    if NO_COLOR or not sys.stdout.isatty():
        return str(text)
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def log(msg: str):
    print(c(msg, "dim"), file=sys.stderr)


def print_table(headers: list[str], rows: list[list[str]], widths: list[int] | None = None):
    if not rows:
        return
    if not widths:
        widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(c(header_line, "bold"))
    try:
        print(c("─" * (sum(widths) + 2 * (len(widths) - 1)), "dim"))
    except UnicodeEncodeError:
        print(c("-" * (sum(widths) + 2 * (len(widths) - 1)), "dim"))
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)))


def print_box(lines: list[str], width: int = 45):
    """Print a box around lines of text."""
    try:
        print("┌" + "─" * width + "┐")
        for line in lines:
            padded = line.ljust(width - 2)[:width - 2]
            print(f"│ {padded} │")
        print("└" + "─" * width + "┘")
    except UnicodeEncodeError:
        # Fallback for terminals that can't render box chars
        print("+" + "-" * width + "+")
        for line in lines:
            padded = line.ljust(width - 2)[:width - 2]
            print(f"| {padded} |")
        print("+" + "-" * width + "+")
